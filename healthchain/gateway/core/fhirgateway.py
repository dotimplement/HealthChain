"""
FHIR Gateway for HealthChain.

This module provides a specialized FHIR integration hub for data aggregation,
transformation, and routing.
"""

import logging
import inspect
import warnings

from contextlib import asynccontextmanager
from typing import (
    Dict,
    List,
    Any,
    Callable,
    Optional,
    TypeVar,
    Type,
)
from fastapi import Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from datetime import datetime

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle
from fhir.resources.capabilitystatement import CapabilityStatement

from healthchain.gateway.core.base import BaseGateway
from healthchain.gateway.core.connection import FHIRConnectionManager
from healthchain.gateway.core.errors import FHIRErrorHandler
from healthchain.gateway.events.fhir import create_fhir_event
from healthchain.gateway.clients.fhir import FHIRServerInterface


logger = logging.getLogger(__name__)

# Type variable for FHIR Resource
T = TypeVar("T", bound=Resource)


class FHIRResponse(JSONResponse):
    """
    Custom response class for FHIR resources.

    This sets the correct content-type header for FHIR resources.
    """

    media_type = "application/fhir+json"


class FHIRGateway(BaseGateway):
    # TODO: move to documentation
    """
    FHIR Gateway for HealthChain.

    A specialized gateway for FHIR resource operations including:
    - Connection pooling and management
    - Resource transformation and aggregation
    - Event-driven processing
    - OAuth2 authentication support

    Example:
        ```python
        # Initialize with connection pooling
        async with FHIRGateway(max_connections=50) as gateway:
            # Add FHIR source
            gateway.add_source("epic", "fhir://epic.org/api/FHIR/R4?...")

            # Register transformation handler
            @gateway.transform(Patient)
            async def enhance_patient(id: str, source: str = None) -> Patient:
                async with gateway.modify(Patient, id, source) as patient:
                    patient.active = True
                    return patient

            # Use the gateway
            patient = await gateway.read(Patient, "123", "epic")
        ```
    """

    def __init__(
        self,
        sources: Dict[str, FHIRServerInterface] = None,
        prefix: str = "/fhir",
        tags: List[str] = ["FHIR"],
        use_events: bool = True,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 5.0,
        **options,
    ):
        """
        Initialize the FHIR Gateway.

        Args:
            sources: Dictionary of named FHIR servers or connection strings
            prefix: URL prefix for API routes
            tags: OpenAPI tags
            use_events: Enable event-based processing
            max_connections: Maximum total HTTP connections across all sources
            max_keepalive_connections: Maximum keep-alive connections per source
            keepalive_expiry: How long to keep connections alive (seconds)
            **options: Additional options
        """
        # Initialize as BaseGateway (which includes APIRouter)
        super().__init__(use_events=use_events, prefix=prefix, tags=tags, **options)

        self.use_events = use_events

        # Create connection manager
        self.connection_manager = FHIRConnectionManager(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        )

        # Add sources if provided
        if sources:
            for name, source in sources.items():
                if isinstance(source, str):
                    self.connection_manager.add_source(name, source)
                else:
                    self.connection_manager.sources[name] = source

        # Handlers for resource operations
        self._resource_handlers: Dict[str, Dict[str, Callable]] = {}

        # Register base routes only (metadata endpoint)
        self._register_base_routes()

    def _get_gateway_dependency(self):
        """Create a dependency function that returns this gateway instance."""

        def get_self_gateway():
            return self

        return get_self_gateway

    def _get_resource_name(self, resource_type: Type[Resource]) -> str:
        """Extract resource name from resource type."""
        return resource_type.__resource_type__

    def _register_base_routes(self):
        """Register basic endpoints"""
        get_self_gateway = self._get_gateway_dependency()

        # FHIR Metadata endpoint - returns CapabilityStatement
        @self.get("/metadata", response_class=FHIRResponse)
        def capability_statement(
            fhir: "FHIRGateway" = Depends(get_self_gateway),
        ):
            """Return the FHIR capability statement for this gateway's services."""
            return fhir.build_capability_statement().model_dump()

        # Gateway status endpoint - returns operational metadata
        @self.get("/status", response_class=JSONResponse)
        def gateway_status(
            fhir: "FHIRGateway" = Depends(get_self_gateway),
        ):
            """Return operational status and metadata for this gateway."""
            return fhir.get_gateway_status()

    def build_capability_statement(self) -> CapabilityStatement:
        """
        Build a FHIR CapabilityStatement for this gateway's value-add services.

        Only includes resources and operations that this gateway provides through
        its transform/aggregate endpoints, not the underlying FHIR sources.

        Returns:
            CapabilityStatement: FHIR-compliant capability statement
        """
        # Build resource entries based on registered handlers
        resources = []
        for resource_type, operations in self._resource_handlers.items():
            interactions = []

            # Add supported interactions based on registered handlers
            for operation in operations:
                if operation == "transform":
                    interactions.append(
                        {"code": "read"}
                    )  # Transform requires read access
                elif operation == "aggregate":
                    interactions.append(
                        {"code": "search-type"}
                    )  # Aggregate is like search

            if interactions:
                # Extract the resource name from the resource type class
                resource_name = self._get_resource_name(resource_type)
                resources.append(
                    {
                        "type": resource_name,
                        "interaction": interactions,
                        "documentation": f"Gateway provides {', '.join(operations)} operations for {resource_name}",
                    }
                )

        capability_data = {
            "resourceType": "CapabilityStatement",
            "status": "active",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "publisher": "HealthChain",
            "kind": "instance",
            "software": {
                "name": "HealthChain FHIR Gateway",
                "version": "1.0.0",  # TODO: Extract from package
            },
            "fhirVersion": "4.0.1",  # TODO: Extract from package
            "format": ["application/fhir+json"],
            "rest": [
                {
                    "mode": "server",
                    "documentation": "HealthChain FHIR Gateway provides transformation and aggregation services",
                    "resource": resources,
                }
            ]
            if resources
            else [],
        }

        return CapabilityStatement(**capability_data)

    @property
    def supported_resources(self) -> List[str]:
        """Get list of supported FHIR resource types."""
        return [
            self._get_resource_name(resource_type)
            for resource_type in self._resource_handlers.keys()
        ]

    def get_capabilities(self) -> List[str]:
        """
        Get list of supported FHIR operations and resources.

        Returns:
            List of capabilities this gateway supports
        """
        capabilities = []
        for resource_type, operations in self._resource_handlers.items():
            resource_name = self._get_resource_name(resource_type)
            for operation in operations:
                capabilities.append(f"{operation}:{resource_name}")
        return capabilities

    def get_gateway_status(self) -> Dict[str, Any]:
        """
        Get operational status and metadata for this gateway.

        This provides gateway-specific operational information.

        Returns:
            Dict containing gateway operational status and metadata
        """
        status = {
            "gateway_type": "FHIRGateway",
            "version": "1.0.0",  # TODO: Extract from package
            "status": "active",
            "timestamp": datetime.now().isoformat() + "Z",
            # Source connectivity
            "sources": {
                "count": len(self.connection_manager.sources),
                "names": list(self.connection_manager.sources.keys()),
            },
            # Connection pool status
            "connection_pool": self.get_pool_status(),
            # Supported operations
            "supported_operations": {
                "resources": self.supported_resources,
                "operations": self.get_capabilities(),
                "endpoints": {
                    "transform": len(
                        [
                            r
                            for r, ops in self._resource_handlers.items()
                            if "transform" in ops
                        ]
                    ),
                    "aggregate": len(
                        [
                            r
                            for r, ops in self._resource_handlers.items()
                            if "aggregate" in ops
                        ]
                    ),
                },
            },
            # Event system status
            "events": {
                "enabled": self.use_events,
                "dispatcher_configured": self.events.dispatcher is not None,
            },
        }

        return status

    def _register_resource_handler(
        self,
        resource_type: Type[Resource],
        operation: str,
        handler: Callable,
    ) -> None:
        """Register a custom handler for a resource operation."""
        self._validate_handler_annotations(resource_type, operation, handler)

        if resource_type not in self._resource_handlers:
            self._resource_handlers[resource_type] = {}
        self._resource_handlers[resource_type][operation] = handler

        resource_name = self._get_resource_name(resource_type)
        logger.debug(
            f"Registered {operation} handler for {resource_name}: {handler.__name__}"
        )

        self._register_operation_route(resource_type, operation)

    def _validate_handler_annotations(
        self,
        resource_type: Type[Resource],
        operation: str,
        handler: Callable,
    ) -> None:
        """Validate that handler annotations match the decorator resource type."""
        if operation != "transform":
            return

        try:
            sig = inspect.signature(handler)
            return_annotation = sig.return_annotation

            if return_annotation == inspect.Parameter.empty:
                warnings.warn(
                    f"Handler {handler.__name__} missing return type annotation for {resource_type.__name__}"
                )
                return

            if return_annotation != resource_type:
                raise TypeError(
                    f"Handler {handler.__name__} return type ({return_annotation}) "
                    f"doesn't match decorator resource type ({resource_type})"
                )

        except Exception as e:
            if isinstance(e, TypeError):
                raise
            logger.warning(f"Could not validate handler annotations: {str(e)}")

    def _register_operation_route(
        self, resource_type: Type[Resource], operation: str
    ) -> None:
        """Register a route for a specific resource type and operation."""
        resource_name = self._get_resource_name(resource_type)

        if operation == "transform":
            path = f"/transform/{resource_name}/{{id}}"
            summary = f"Transform {resource_name}"
            description = (
                f"Transform a {resource_name} resource with registered handler"
            )
        elif operation == "aggregate":
            path = f"/aggregate/{resource_name}"
            summary = f"Aggregate {resource_name}"
            description = f"Aggregate {resource_name} resources from multiple sources"
        else:
            raise ValueError(f"Unsupported operation: {operation}")

        handler = self._create_route_handler(resource_type, operation)

        self.add_api_route(
            path=path,
            endpoint=handler,
            methods=["GET"],
            summary=summary,
            description=description,
            response_model_exclude_none=True,
            response_class=FHIRResponse,
            tags=self.tags,
            include_in_schema=True,
        )
        logger.debug(f"Registered {operation} endpoint: {self.prefix}{path}")

    def _create_route_handler(
        self, resource_type: Type[Resource], operation: str
    ) -> Callable:
        """Create a route handler for the given resource type and operation."""
        get_self_gateway = self._get_gateway_dependency()

        def _execute_handler(fhir: "FHIRGateway", *args) -> Any:
            """Common handler execution logic with error handling."""
            try:
                handler_func = fhir._resource_handlers[resource_type][operation]
                result = handler_func(*args)
                return result
            except Exception as e:
                logger.error(f"Error in {operation} handler: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        if operation == "transform":

            async def handler(
                id: str = Path(..., description="Resource ID to transform"),
                source: Optional[str] = Query(
                    None, description="Source system to retrieve the resource from"
                ),
                fhir: "FHIRGateway" = Depends(get_self_gateway),
            ):
                """Transform a resource with registered handler."""
                return _execute_handler(fhir, id, source)

        elif operation == "aggregate":

            async def handler(
                id: Optional[str] = Query(None, description="ID to aggregate data for"),
                sources: Optional[List[str]] = Query(
                    None, description="List of source names to query"
                ),
                fhir: "FHIRGateway" = Depends(get_self_gateway),
            ):
                """Aggregate resources with registered handler."""
                return _execute_handler(fhir, id, sources)

        else:
            raise ValueError(f"Unsupported operation: {operation}")

        return handler

    def add_source(self, name: str, connection_string: str) -> None:
        """
        Add a FHIR data source using connection string with OAuth2.0 flow.

        Format: fhir://hostname:port/path?param1=value1&param2=value2

        Examples:
            fhir://epic.org/api/FHIR/R4?client_id=my_app&client_secret=secret&token_url=https://epic.org/oauth2/token&scope=system/*.read
            fhir://cerner.org/r4?client_id=app_id&client_secret=app_secret&token_url=https://cerner.org/token&audience=https://cerner.org/fhir
        """
        return self.connection_manager.add_source(name, connection_string)

    async def get_client(self, source: str = None) -> FHIRServerInterface:
        """
        Get a FHIR client for the specified source.

        Args:
            source: Source name to get client for (uses first available if None)

        Returns:
            FHIRServerInterface: A FHIR client with pooled connections

        Raises:
            ValueError: If source is unknown or no connection string found
        """
        return await self.connection_manager.get_client(source)

    async def capabilities(self, source: str = None) -> CapabilityStatement:
        """
        Get the capabilities of the FHIR server.

        Args:
            source: Source name to get capabilities for (uses first available if None)

        Returns:
            CapabilityStatement: The capabilities of the FHIR server

        Raises:
            FHIRConnectionError: If connection fails
        """
        capabilities = await self._execute_with_client(
            "capabilities",
            source=source,
            resource_type=CapabilityStatement,
        )

        # Emit capabilities event
        self._emit_fhir_event("capabilities", "CapabilityStatement", None, capabilities)
        logger.debug("Retrieved server capabilities")

        return capabilities

    async def read(
        self,
        resource_type: Type[Resource],
        fhir_id: str,
        source: str = None,
    ) -> Resource:
        """
        Read a FHIR resource.

        Args:
            resource_type: The FHIR resource type class
            fhir_id: Resource ID to fetch
            source: Source name to fetch from (uses first available if None)

        Returns:
            The FHIR resource object

        Raises:
            ValueError: If resource not found or source invalid
            FHIRConnectionError: If connection fails

        Example:
            # Simple read-only access
            document = await fhir_gateway.read(DocumentReference, "123", "epic")
            summary = extract_summary(document.text)
        """
        resource = await self._execute_with_client(
            "read",
            source=source,
            resource_type=resource_type,
            resource_id=fhir_id,
            client_args=(resource_type, fhir_id),
        )

        if not resource:
            type_name = resource_type.__resource_type__
            raise ValueError(f"Resource {type_name}/{fhir_id} not found")

        # Emit read event
        type_name = resource.__resource_type__
        self._emit_fhir_event("read", type_name, fhir_id, resource)
        logger.debug(f"Retrieved {type_name}/{fhir_id} for read-only access")

        return resource

    async def search(
        self,
        resource_type: Type[Resource],
        params: Dict[str, Any] = None,
        source: str = None,
    ) -> Bundle:
        """
        Search for FHIR resources.

        Args:
            resource_type: The FHIR resource type class
            params: Search parameters (e.g., {"name": "Smith", "active": "true"})
            source: Source name to search in (uses first available if None)

        Returns:
            Bundle containing search results

        Raises:
            ValueError: If source is invalid
            FHIRConnectionError: If connection fails

        Example:
            # Search for patients by name
            bundle = await fhir_gateway.search(Patient, {"name": "Smith"}, "epic")
            for entry in bundle.entry or []:
                patient = entry.resource
                print(f"Found patient: {patient.name[0].family}")
        """
        bundle = await self._execute_with_client(
            "search",
            source=source,
            resource_type=resource_type,
            client_args=(resource_type,),
            client_kwargs={"params": params},
        )

        # Emit search event with result count
        type_name = resource_type.__resource_type__
        event_data = {
            "params": params,
            "result_count": len(bundle.entry) if bundle.entry else 0,
        }
        self._emit_fhir_event("search", type_name, None, event_data)
        logger.debug(
            f"Searched {type_name} with params {params}, found {len(bundle.entry) if bundle.entry else 0} results"
        )

        return bundle

    async def create(self, resource: Resource, source: str = None) -> Resource:
        """
        Create a new FHIR resource.

        Args:
            resource: The FHIR resource to create
            source: Source name to create in (uses first available if None)

        Returns:
            The created FHIR resource with server-assigned ID

        Raises:
            ValueError: If source is invalid
            FHIRConnectionError: If connection fails

        Example:
            # Create a new patient
            patient = Patient(name=[HumanName(family="Smith", given=["John"])])
            created = await fhir_gateway.create(patient, "epic")
            print(f"Created patient with ID: {created.id}")
        """
        created = await self._execute_with_client(
            "create",
            source=source,
            resource_type=resource.__class__,
            client_args=(resource,),
        )

        # Emit create event
        type_name = resource.__resource_type__
        self._emit_fhir_event("create", type_name, created.id, created)
        logger.debug(f"Created {type_name} resource with ID {created.id}")

        return created

    async def update(self, resource: Resource, source: str = None) -> Resource:
        """
        Update an existing FHIR resource.

        Args:
            resource: The FHIR resource to update (must have ID)
            source: Source name to update in (uses first available if None)

        Returns:
            The updated FHIR resource

        Raises:
            ValueError: If resource has no ID or source is invalid
            FHIRConnectionError: If connection fails

        Example:
            # Update a patient's name
            patient = await fhir_gateway.read(Patient, "123", "epic")
            patient.name[0].family = "Jones"
            updated = await fhir_gateway.update(patient, "epic")
        """
        if not resource.id:
            raise ValueError("Resource must have an ID for update")

        updated = await self._execute_with_client(
            "update",
            source=source,
            resource_type=resource.__class__,
            resource_id=resource.id,
            client_args=(resource,),
        )

        # Emit update event
        type_name = resource.__resource_type__
        self._emit_fhir_event("update", type_name, resource.id, updated)
        logger.debug(f"Updated {type_name} resource with ID {resource.id}")

        return updated

    async def delete(
        self, resource_type: Type[Resource], fhir_id: str, source: str = None
    ) -> bool:
        """
        Delete a FHIR resource.

        Args:
            resource_type: The FHIR resource type class
            fhir_id: Resource ID to delete
            source: Source name to delete from (uses first available if None)

        Returns:
            True if deletion was successful

        Raises:
            ValueError: If source is invalid
            FHIRConnectionError: If connection fails

        Example:
            # Delete a patient
            success = await fhir_gateway.delete(Patient, "123", "epic")
            if success:
                print("Patient deleted successfully")
        """
        success = await self._execute_with_client(
            "delete",
            source=source,
            resource_type=resource_type,
            resource_id=fhir_id,
            client_args=(resource_type, fhir_id),
        )

        if success:
            # Emit delete event
            type_name = resource_type.__resource_type__
            self._emit_fhir_event("delete", type_name, fhir_id, None)
            logger.debug(f"Deleted {type_name} resource with ID {fhir_id}")

        return success

    async def transaction(self, bundle: Bundle, source: str = None) -> Bundle:
        """
        Execute a FHIR transaction bundle.

        Args:
            bundle: The transaction bundle to execute
            source: Source name to execute in (uses first available if None)

        Returns:
            The response bundle with results

        Raises:
            ValueError: If source is invalid
            FHIRConnectionError: If connection fails

        Example:
            # Create a transaction bundle
            bundle = Bundle(type="transaction", entry=[
                BundleEntry(resource=patient1, request=BundleRequest(method="POST")),
                BundleEntry(resource=patient2, request=BundleRequest(method="POST"))
            ])
            result = await fhir_gateway.transaction(bundle, "epic")
        """
        result = await self._execute_with_client(
            "transaction",
            source=source,
            resource_type=Bundle,
            client_args=(bundle,),
        )

        # Emit transaction event with entry counts
        event_data = {
            "entry_count": len(bundle.entry) if bundle.entry else 0,
            "result_count": len(result.entry) if result.entry else 0,
        }
        self._emit_fhir_event("transaction", "Bundle", None, event_data)
        logger.debug(
            f"Executed transaction bundle with {len(bundle.entry) if bundle.entry else 0} entries"
        )

        return result

    @asynccontextmanager
    async def modify(
        self, resource_type: Type[Resource], fhir_id: str = None, source: str = None
    ):
        """
        Context manager for working with FHIR resources.

        Automatically handles fetching, updating, and error handling using connection pooling.

        Args:
            resource_type: The FHIR resource type class (e.g. Patient)
            fhir_id: Resource ID (if None, creates a new resource)
            source: Source name to use (uses first available if None)

        Yields:
            Resource: The FHIR resource object

        Raises:
            FHIRConnectionError: If connection fails
            ValueError: If resource type is invalid
        """
        client = await self.get_client(source)
        resource = None
        is_new = fhir_id is None

        # Get type name for error messages
        type_name = resource_type.__resource_type__

        try:
            if is_new:
                resource = resource_type()
            else:
                resource = await client.read(resource_type, fhir_id)
                logger.debug(f"Retrieved {type_name}/{fhir_id} in modify context")
                self._emit_fhir_event("read", type_name, fhir_id, resource)

            yield resource

            if is_new:
                updated_resource = await client.create(resource)
            else:
                updated_resource = await client.update(resource)

            resource.id = updated_resource.id
            for field_name, field_value in updated_resource.model_dump().items():
                if hasattr(resource, field_name):
                    setattr(resource, field_name, field_value)

            operation = "create" if is_new else "update"
            self._emit_fhir_event(operation, type_name, resource.id, updated_resource)
            logger.debug(
                f"{'Created' if is_new else 'Updated'} {type_name} resource in modify context"
            )

        except Exception as e:
            operation = (
                "read"
                if not is_new and resource is None
                else "create"
                if is_new
                else "update"
            )
            FHIRErrorHandler.handle_fhir_error(e, type_name, fhir_id, operation)

    def aggregate(self, resource_type: Type[Resource]):
        """
        Decorator for custom aggregation functions.

        Args:
            resource_type: The FHIR resource type class that this handler aggregates

        Example:
            @fhir_gateway.aggregate(Patient)
            def aggregate_patients(id: str = None, sources: List[str] = None) -> List[Patient]:
                # Handler implementation
                pass
        """

        def decorator(handler: Callable):
            self._register_resource_handler(resource_type, "aggregate", handler)
            return handler

        return decorator

    def transform(self, resource_type: Type[Resource]):
        """
        Decorator for custom transformation functions.

        Args:
            resource_type: The FHIR resource type class that this handler transforms

        Example:
            @fhir_gateway.transform(DocumentReference)
            def transform_document(id: str, source: str = None) -> DocumentReference:
                # Handler implementation
                pass
        """

        def decorator(handler: Callable):
            self._register_resource_handler(resource_type, "transform", handler)
            return handler

        return decorator

    def _emit_fhir_event(
        self, operation: str, resource_type: str, resource_id: str, resource: Any = None
    ):
        """
        Emit an event for FHIR operations.

        Args:
            operation: The FHIR operation (read, search, create, update, delete)
            resource_type: The FHIR resource type
            resource_id: The resource ID
            resource: The resource object or data
        """
        self.events.emit_event(
            create_fhir_event,
            operation,
            resource_type,
            resource_id,
            resource,
            use_events=self.use_events,
        )

    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get the current status of the connection pool.

        Returns:
            Dict containing pool status information including:
            - max_connections: Maximum connections across all sources
            - sources: Dict of source names and their connection info
            - client_stats: Detailed httpx connection pool statistics
        """
        return self.connection_manager.get_pool_status()

    async def close(self):
        """Close all connections and clean up resources."""
        await self.connection_manager.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _execute_with_client(
        self,
        operation: str,
        *,  # Force keyword-only arguments
        source: str = None,
        resource_type: Type[Resource] = None,
        resource_id: str = None,
        client_args: tuple = (),
        client_kwargs: dict = None,
    ):
        """
        Execute a client operation with consistent error handling.

        Args:
            operation: Operation name (read, create, update, delete, etc.)
            source: Source name to use
            resource_type: Resource type for error handling
            resource_id: Resource ID for error handling (if applicable)
            client_args: Positional arguments to pass to the client method
            client_kwargs: Keyword arguments to pass to the client method
        """
        client = await self.get_client(source)
        client_kwargs = client_kwargs or {}

        try:
            result = await getattr(client, operation)(*client_args, **client_kwargs)
            return result

        except Exception as e:
            # Use existing error handler
            error_resource_type = resource_type or (
                client_args[0].__class__
                if client_args and hasattr(client_args[0], "__class__")
                else None
            )
            FHIRErrorHandler.handle_fhir_error(
                e, error_resource_type, resource_id, operation
            )
