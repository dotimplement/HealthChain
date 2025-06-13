"""
FHIR Gateway for HealthChain.

This module provides a specialized FHIR integration hub for data aggregation,
transformation, and routing.
"""

import logging
import inspect
import warnings

from contextlib import asynccontextmanager
from datetime import datetime
from typing import (
    Dict,
    List,
    Any,
    Callable,
    Optional,
    TypeVar,
    Union,
    Type,
    TYPE_CHECKING,
)
from fastapi import Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle
from fhir.resources.capabilitystatement import CapabilityStatement

from healthchain.gateway.core.base import BaseGateway
from healthchain.gateway.core.connection import FHIRConnectionManager
from healthchain.gateway.core.errors import FHIRErrorHandler
from healthchain.gateway.events.dispatcher import (
    EHREvent,
    EHREventType,
    EventDispatcher,
)
from healthchain.gateway.api.protocols import FHIRGatewayProtocol
from healthchain.gateway.clients.fhir import FHIRServerInterface

# Import for type hints - will be available at runtime through local imports
if TYPE_CHECKING:
    from healthchain.gateway.clients.auth import FHIRAuthConfig


logger = logging.getLogger(__name__)

# Type variable for FHIR Resource
T = TypeVar("T", bound=Resource)

OPERATION_TO_EVENT = {
    "read": EHREventType.FHIR_READ,
    "search": EHREventType.FHIR_SEARCH,
    "create": EHREventType.FHIR_CREATE,
    "update": EHREventType.FHIR_UPDATE,
    "delete": EHREventType.FHIR_DELETE,
}


class FHIRResponse(JSONResponse):
    """
    Custom response class for FHIR resources.

    This sets the correct content-type header for FHIR resources.
    """

    media_type = "application/fhir+json"


class FHIRGateway(BaseGateway, FHIRGatewayProtocol):
    # TODO: move to documentation
    """
    FHIR integration hub with automatic connection pooling and lifecycle management.
    Provides value-add endpoints for data aggregation and transformation.

    Example:
        ```python
        from fhir.resources.patient import Patient
        from fhir.resources.documentreference import DocumentReference
        from healthchain.gateway import FHIRGateway
        from healthchain.gateway.api.app import HealthChainAPI

        app = HealthChainAPI()
        fhir_gateway = FHIRGateway()

        # Configure sources
        fhir_gateway.add_source("epic", "fhir://r4.epic.com/api/FHIR/R4?auth=oauth&timeout=30")
        fhir_gateway.add_source("cerner", "fhir://cernercare.com/r4?auth=basic&username=user&password=pass")

        # Transform handler
        @fhir_gateway.transform(DocumentReference)
        async def enhance_document(id: str, source: str = None) -> DocumentReference:
            document = await fhir_gateway.get_resource(DocumentReference, id, source)
            async with fhir_gateway.resource_context(DocumentReference, id, source) as doc:
                doc.description = "Enhanced by HealthChain"
                if not doc.extension:
                    doc.extension = []
                doc.extension.append({
                    "url": "http://healthchain.org/extension/processed",
                    "valueDateTime": datetime.now().isoformat()
                })
                return doc


        # Endpoints: /fhir/transform/DocumentReference/{id}?source=epic
        #            /fhir/aggregate/Patient?id=123&sources=epic&sources=cerner
        ```
    """

    def __init__(
        self,
        sources: Dict[str, Union[FHIRServerInterface, str]] = None,
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
        # Handler-specific routes will be registered when the app is ready
        self._routes_registered = False

    def _register_base_routes(self):
        """Register basic endpoints"""

        # Dependency for this gateway instance
        def get_self_gateway():
            return self

        # Metadata endpoint
        @self.get("/metadata", response_class=FHIRResponse)
        def capability_statement(
            fhir: FHIRGatewayProtocol = Depends(get_self_gateway),
        ):
            """Return the FHIR capability statement."""
            return {
                "resourceType": "CapabilityStatement",
                "status": "active",
                "fhirVersion": "4.0.1",
                "format": ["application/fhir+json"],
                "rest": [
                    {
                        "mode": "server",
                        "resource": [
                            {
                                "type": resource_type,
                                "interaction": [
                                    {"code": "read"},
                                    {"code": "search-type"},
                                ],
                            }
                            for resource_type in [
                                "Patient"
                            ]  # TODO: should extract from servers
                        ],
                    }
                ],
            }

    def _register_handler_routes(self) -> None:
        """
        Register routes for all handlers directly on the gateway.

        This ensures all routes get the router's prefix automatically.
        """
        # Register transform and aggregate routes for each resource type
        for resource_type, operations in self._resource_handlers.items():
            if "transform" in operations:
                self._register_transform_route(resource_type)

            if "aggregate" in operations:
                self._register_aggregate_route(resource_type)

        # Mark routes as registered
        self._routes_registered = True

    def _register_transform_route(self, resource_type: str) -> None:
        """Register a transform route for a specific resource type."""
        # Get resource type name
        if hasattr(resource_type, "__resource_type__"):
            resource_name = resource_type.__resource_type__
        elif isinstance(resource_type, str):
            resource_name = resource_type
        else:
            resource_name = getattr(resource_type, "__name__", str(resource_type))

        # Create the transform path
        transform_path = f"/transform/{resource_name}/{{id}}"

        # Dependency for this gateway instance
        def get_self_gateway():
            return self

        # Create a closure to capture the resource_type
        def create_transform_handler(res_type):
            async def transform_handler(
                id: str = Path(..., description="Resource ID to transform"),
                source: Optional[str] = Query(
                    None, description="Source system to retrieve the resource from"
                ),
                fhir: FHIRGatewayProtocol = Depends(get_self_gateway),
            ):
                """Transform a resource with registered handler."""
                # Get the handler for this resource type
                handler = fhir._resource_handlers[res_type]["transform"]

                # Execute the handler and return the result
                try:
                    result = handler(id, source)

                    # Validate the result matches expected type
                    validated_result = fhir._validate_handler_result(
                        result, res_type, handler.__name__
                    )

                    return validated_result
                except Exception as e:
                    logger.error(f"Error in transform handler: {str(e)}")
                    raise HTTPException(status_code=500, detail=str(e))

            return transform_handler

        # Add the route directly to the gateway
        self.add_api_route(
            path=transform_path,
            endpoint=create_transform_handler(resource_type),
            methods=["GET"],
            summary=f"Transform {resource_name}",
            description=f"Transform a {resource_name} resource with registered handler",
            response_model_exclude_none=True,
            response_class=FHIRResponse,
            tags=self.tags,
            include_in_schema=True,
        )
        logger.debug(f"Registered transform endpoint: {self.prefix}{transform_path}")

    def _register_aggregate_route(self, resource_type: str) -> None:
        """Register an aggregate route for a specific resource type."""
        # Get resource type name
        if hasattr(resource_type, "__resource_type__"):
            resource_name = resource_type.__resource_type__
        elif isinstance(resource_type, str):
            resource_name = resource_type
        else:
            resource_name = getattr(resource_type, "__name__", str(resource_type))

        # Create the aggregate path
        aggregate_path = f"/aggregate/{resource_name}"

        # Dependency for this gateway instance
        def get_self_gateway():
            return self

        # Create a closure to capture the resource_type
        def create_aggregate_handler(res_type):
            async def aggregate_handler(
                id: Optional[str] = Query(None, description="ID to aggregate data for"),
                sources: Optional[List[str]] = Query(
                    None, description="List of source names to query"
                ),
                fhir: FHIRGatewayProtocol = Depends(get_self_gateway),
            ):
                """Aggregate resources with registered handler."""
                # Get the handler for this resource type
                handler = fhir._resource_handlers[res_type]["aggregate"]

                # Execute the handler and return the result
                try:
                    result = handler(id, sources)

                    # For aggregate operations, result might be a list or bundle
                    # Validate if it's a single resource
                    if hasattr(result, "resourceType"):
                        validated_result = fhir._validate_handler_result(
                            result, res_type, handler.__name__
                        )
                        return validated_result

                    return result
                except Exception as e:
                    logger.error(f"Error in aggregate handler: {str(e)}")
                    raise HTTPException(status_code=500, detail=str(e))

            return aggregate_handler

        # Add the route directly to the gateway
        self.add_api_route(
            path=aggregate_path,
            endpoint=create_aggregate_handler(resource_type),
            methods=["GET"],
            summary=f"Aggregate {resource_name}",
            description=f"Aggregate {resource_name} resources from multiple sources",
            response_model_exclude_none=True,
            response_class=FHIRResponse,
            tags=self.tags,
            include_in_schema=True,
        )
        logger.debug(f"Registered aggregate endpoint: {self.prefix}{aggregate_path}")

    def _register_resource_handler(
        self,
        resource_type: Union[str, Type[Resource]],
        operation: str,
        handler: Callable,
    ):
        """Register a custom handler for a resource operation."""
        self._validate_handler_annotations(resource_type, operation, handler)

        if resource_type not in self._resource_handlers:
            self._resource_handlers[resource_type] = {}
        self._resource_handlers[resource_type][operation] = handler

        # Log the registration
        resource_name = getattr(resource_type, "__resource_type__", str(resource_type))
        logger.debug(
            f"Registered {operation} handler for {resource_name}: {handler.__name__}"
        )

        # Register this specific route immediately
        if operation == "transform":
            self._register_transform_route(resource_type)
        elif operation == "aggregate":
            self._register_aggregate_route(resource_type)

    def _validate_handler_annotations(
        self,
        resource_type: Union[str, Type[Resource]],
        operation: str,
        handler: Callable,
    ):
        """
        Validate that handler annotations match the decorator resource type.

        Args:
            resource_type: The resource type from the decorator
            operation: The operation being registered (transform, aggregate)
            handler: The handler function to validate

        Raises:
            TypeError: If annotations don't match or are missing
        """
        try:
            # Get handler signature
            sig = inspect.signature(handler)

            # Check return type annotation for transform operations
            if operation == "transform":
                return_annotation = sig.return_annotation

                if return_annotation == inspect.Parameter.empty:
                    warnings.warn(
                        f"Handler {handler.__name__} for {operation} operation "
                        f"should have a return type annotation matching {resource_type}"
                    )
                elif return_annotation != resource_type:
                    # Try to compare by name if direct comparison fails
                    resource_name = getattr(
                        resource_type, "__name__", str(resource_type)
                    )
                    return_name = getattr(
                        return_annotation, "__name__", str(return_annotation)
                    )

                    if resource_name != return_name:
                        error_msg = (
                            f"Handler {handler.__name__} return type annotation "
                            f"({return_annotation}) doesn't match decorator resource type "
                            f"({resource_type}). They must be identical for type safety."
                        )
                        logger.error(error_msg)
                        raise TypeError(error_msg)

            # Check if handler expects resource_type parameter (for future enhancement)
            if "resource_type" in sig.parameters:
                param = sig.parameters["resource_type"]
                if param.annotation not in (Type[Resource], inspect.Parameter.empty):
                    warnings.warn(
                        f"Handler {handler.__name__} has resource_type parameter "
                        f"with annotation {param.annotation}. Consider using Type[Resource] "
                        f"for better type safety."
                    )

        except TypeError as e:
            # Re-raise TypeError to prevent registration of invalid handlers
            raise e
        except Exception as e:
            logger.warning(f"Could not validate handler annotations: {str(e)}")

    def _validate_handler_result(
        self, result: Any, expected_type: Union[str, Type[Resource]], handler_name: str
    ) -> Any:
        """
        Validate that handler result matches expected resource type.

        Args:
            result: The result returned by the handler
            expected_type: The expected resource type
            handler_name: Name of the handler for error reporting

        Returns:
            The validated result

        Raises:
            TypeError: If result type doesn't match expected type
        """
        if result is None:
            return result

        # For FHIR Resource types, check inheritance
        if hasattr(expected_type, "__mro__") and issubclass(expected_type, Resource):
            if not isinstance(result, expected_type):
                raise TypeError(
                    f"Handler {handler_name} returned {type(result)} "
                    f"but expected {expected_type}. Ensure the handler returns "
                    f"the correct FHIR resource type."
                )

        # For string resource types, check resourceType attribute
        elif isinstance(expected_type, str):
            if hasattr(result, "resourceType"):
                if result.resourceType != expected_type:
                    raise TypeError(
                        f"Handler {handler_name} returned resource with type "
                        f"'{result.resourceType}' but expected '{expected_type}'"
                    )
            else:
                logger.warning(
                    f"Cannot validate resource type for result from {handler_name}: "
                    f"no resourceType attribute found"
                )

        return result

    def add_source(self, name: str, connection_string: str):
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

        Connections are automatically pooled and managed by httpx.

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
        try:
            client = await self.get_client(source)
            capabilities = await client.capabilities()

            # Emit capabilities event
            self._emit_fhir_event(
                "capabilities", "CapabilityStatement", None, capabilities
            )
            logger.debug("Retrieved server capabilities")

            return capabilities

        except Exception as e:
            FHIRErrorHandler.handle_fhir_error(
                e, "CapabilityStatement", None, "capabilities"
            )

    async def read(
        self,
        resource_type: Union[str, Type[Resource]],
        fhir_id: str,
        source: str = None,
    ) -> Resource:
        """
        Read a FHIR resource.

        Args:
            resource_type: The FHIR resource type (class or string)
            fhir_id: Resource ID to fetch
            source: Source name to fetch from (uses first available if None)

        Returns:
            The FHIR resource object

        Raises:
            ValueError: If resource not found or source invalid
            FHIRConnectionError: If connection fails

        Example:
            # Simple read-only access
            document = await fhir_gateway.get_resource(DocumentReference, "123", "epic")
            summary = extract_summary(document.text)
        """
        client = await self.get_client(source)

        try:
            # Fetch the resource
            resource = await client.read(resource_type, fhir_id)
            if not resource:
                # Get type name for error message
                type_name = getattr(resource_type, "__name__", str(resource_type))
                raise ValueError(f"Resource {type_name}/{fhir_id} not found")

            # Get type name for event emission
            type_name = resource.__resource_type__

            # Emit read event
            self._emit_fhir_event("read", type_name, fhir_id, resource)

            logger.debug(f"Retrieved {type_name}/{fhir_id} for read-only access")

            return resource

        except Exception as e:
            FHIRErrorHandler.handle_fhir_error(e, resource_type, fhir_id, "read")

    async def search(
        self,
        resource_type: Union[str, Type[Resource]],
        params: Dict[str, Any] = None,
        source: str = None,
    ) -> Bundle:
        """
        Search for FHIR resources.

        Args:
            resource_type: The FHIR resource type (class or string)
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
        client = await self.get_client(source)

        try:
            bundle = await client.search(resource_type, params)

            # Get type name for event emission
            if hasattr(resource_type, "__name__"):
                type_name = resource_type.__name__
            else:
                type_name = str(resource_type)

            # Emit search event
            self._emit_fhir_event(
                "search",
                type_name,
                None,
                {
                    "params": params,
                    "result_count": len(bundle.entry) if bundle.entry else 0,
                },
            )

            logger.debug(
                f"Searched {type_name} with params {params}, found {len(bundle.entry) if bundle.entry else 0} results"
            )

            return bundle

        except Exception as e:
            FHIRErrorHandler.handle_fhir_error(e, resource_type, None, "search")

    @asynccontextmanager
    async def modify(self, resource_type: str, fhir_id: str = None, source: str = None):
        """
        Context manager for working with FHIR resources.

        Automatically handles fetching, updating, and error handling using connection pooling.

        Args:
            resource_type: The FHIR resource type (e.g. 'Patient')
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
        type_name = (
            resource_type.__name__
            if hasattr(resource_type, "__name__")
            else str(resource_type)
        )

        try:
            if is_new:
                import importlib

                resource_module = importlib.import_module(
                    f"fhir.resources.{type_name.lower()}"
                )
                resource_class = getattr(resource_module, type_name)
                resource = resource_class()
            else:
                resource = await client.read(resource_type, fhir_id)
                logger.debug(f"Retrieved {type_name}/{fhir_id} in modify context")
                self._emit_fhir_event("read", type_name, fhir_id, resource)

            yield resource

            updated_resource = await client.update(resource)
            resource.id = updated_resource.id
            for field_name, field_value in updated_resource.model_dump().items():
                if hasattr(resource, field_name):
                    setattr(resource, field_name, field_value)

            event_type = "create" if is_new else "update"
            self._emit_fhir_event(event_type, type_name, resource.id, updated_resource)
            logger.debug(
                f"{'Created' if is_new else 'Updated'} {type_name} resource in modify context"
            )

        except Exception as e:
            FHIRErrorHandler.handle_fhir_error(
                e, type_name, fhir_id, "read" if not is_new else "create"
            )

    @property
    def supported_resources(self) -> List[str]:
        """Get list of supported FHIR resource types."""
        return list(self._resource_handlers.keys())

    def aggregate(self, resource_type: Union[str, Type[Resource]]):
        """
        Decorator for custom aggregation functions.

        Args:
            resource_type: The FHIR resource type (class or string) that this handler aggregates

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

    def transform(self, resource_type: Union[str, Type[Resource]]):
        """
        Decorator for custom transformation functions.

        Args:
            resource_type: The FHIR resource type (class or string) that this handler transforms

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

    def set_event_dispatcher(self, event_dispatcher: Optional[EventDispatcher] = None):
        """
        Set the event dispatcher for this gateway.

        Args:
            event_dispatcher: The event dispatcher to use

        Returns:
            Self, for method chaining
        """
        # Directly set the attribute instead of using super() to avoid inheritance issues
        self.event_dispatcher = event_dispatcher
        # Register default handlers if needed
        self._register_default_handlers()
        return self

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
        # Skip if events are disabled or no dispatcher
        if not self.use_events or not self.event_dispatcher:
            return

        # Get the event type from the mapping
        event_type = OPERATION_TO_EVENT.get(operation)
        if not event_type:
            return

        # If a custom event creator is defined, use it
        if self._event_creator:
            event = self._event_creator(operation, resource_type, resource_id, resource)
            if event:
                self._run_async_publish(event)
            return

        # Create a standard event
        event = EHREvent(
            event_type=event_type,
            source_system="FHIR",
            timestamp=datetime.now(),
            payload={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "operation": operation,
            },
        )

        # Add the resource data if available
        if resource:
            event.payload["resource"] = resource

        # Publish the event
        self._run_async_publish(event)

    def get_capabilities(self) -> List[str]:
        """
        Get list of supported FHIR operations and resources.

        Returns:
            List of capabilities this gateway supports
        """
        capabilities = []

        # Add resource-level capabilities
        for resource_type, operations in self._resource_handlers.items():
            for operation in operations:
                capabilities.append(f"{operation}:{resource_type}")

        return capabilities

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

    def add_source_config(self, name: str, auth_config: "FHIRAuthConfig"):
        """
        Add a FHIR data source using a configuration object.

        This is an alternative to connection strings for those who prefer
        explicit configuration objects.

        Args:
            name: Source name
            auth_config: FHIRAuthConfig object with OAuth2 settings

        Example:
            from healthchain.gateway.clients.auth import FHIRAuthConfig

            config = FHIRAuthConfig(
                client_id="your_client_id",
                client_secret="your_client_secret",
                token_url="https://epic.com/oauth2/token",
                base_url="https://epic.com/api/FHIR/R4",
                scope="system/Patient.read"
            )
            fhir_gateway.add_source_config("epic", config)
        """
        return self.connection_manager.add_source_config(name, auth_config)

    def add_source_from_env(self, name: str, env_prefix: str):
        """
        Add a FHIR data source using environment variables.

        This method reads OAuth2.0 configuration from environment variables
        with a given prefix.

        Args:
            name: Source name
            env_prefix: Environment variable prefix (e.g., "EPIC")

        Expected environment variables:
            {env_prefix}_CLIENT_ID
            {env_prefix}_CLIENT_SECRET
            {env_prefix}_TOKEN_URL
            {env_prefix}_BASE_URL
            {env_prefix}_SCOPE (optional)
            {env_prefix}_AUDIENCE (optional)
            {env_prefix}_TIMEOUT (optional, default: 30)
            {env_prefix}_VERIFY_SSL (optional, default: true)

        Example:
            # Set environment variables:
            # EPIC_CLIENT_ID=app123
            # EPIC_CLIENT_SECRET=secret456
            # EPIC_TOKEN_URL=https://epic.com/oauth2/token
            # EPIC_BASE_URL=https://epic.com/api/FHIR/R4

            fhir_gateway.add_source_from_env("epic", "EPIC")
        """
        return self.connection_manager.add_source_from_env(name, env_prefix)

    async def close(self):
        """Close all connections and clean up resources."""
        await self.connection_manager.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
