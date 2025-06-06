"""
FHIR Gateway for HealthChain.

This module provides a specialized FHIR integration hub for data aggregation,
transformation, and routing.
"""

import logging
import urllib.parse
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
)
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse

from fhir.resources.resource import Resource

from healthchain.gateway.core.base import BaseGateway
from healthchain.gateway.events.dispatcher import (
    EHREvent,
    EHREventType,
    EventDispatcher,
)
from healthchain.gateway.api.protocols import FHIRGatewayProtocol
from healthchain.gateway.clients import FHIRServerInterface


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


class FHIRConnectionError(Exception):
    """Standardized FHIR connection error with state codes."""

    def __init__(self, message: str, code: str, state: str = None):
        self.message = message
        self.code = code
        self.state = state
        super().__init__(f"[{code}] {message}")


class FHIRConnectionPool:
    """Connection pool for FHIR servers to improve performance."""

    def __init__(self, max_connections: int = 10):
        self._connections: Dict[str, List[FHIRServerInterface]] = {}
        self.max_connections = max_connections

    def get_connection(
        self, connection_string: str, server_factory
    ) -> FHIRServerInterface:
        """Get a connection from the pool or create a new one."""
        if connection_string not in self._connections:
            self._connections[connection_string] = []

        # Return existing connection if available
        if self._connections[connection_string]:
            return self._connections[connection_string].pop()

        # Create new connection
        return server_factory(connection_string)

    def release_connection(self, connection_string: str, server: FHIRServerInterface):
        """Return a connection to the pool."""
        if connection_string not in self._connections:
            self._connections[connection_string] = []

        # Only keep up to max_connections
        if len(self._connections[connection_string]) < self.max_connections:
            self._connections[connection_string].append(server)


class FHIRResponse(JSONResponse):
    """
    Custom response class for FHIR resources.

    This sets the correct content-type header for FHIR resources.
    """

    media_type = "application/fhir+json"


class FHIRGateway(BaseGateway, APIRouter, FHIRGatewayProtocol):
    """
    FHIR integration hub for data aggregation, transformation, and routing.

    Adds value-add endpoints like /aggregate and /transform.

    Example:
        ```python
        # Create a FHIR gateway
        from fhir.resources.patient import Patient
        from healthchain.gateway.clients import FHIRGateway
        from healthchain.gateway.api.app import HealthChainAPI

        app = HealthChainAPI()

        # Using connection strings
        fhir_gateway = FHIRGateway()
        fhir_gateway.add_source("epic", "fhir://r4.epic.com/api/FHIR/R4?auth=oauth&timeout=30")
        fhir_gateway.add_source("cerner", "fhir://cernercare.com/r4?auth=basic&username=user&password=pass")

        # Register a custom read handler using decorator
        @fhir_gateway.transform(Patient)
        def transform_patient(patient_id: str) -> Patient:
            patient = fhir_gateway.sources["epic"].read(Patient, patient_id)
            # Apply US Core profile transformation
            patient = profile_transform(patient, "us-core")
            fhir_gateway.sources["my_app"].update(patient)
            return patient

        # Using resource context manager
        with fhir_gateway.resource_context("Patient", id="123", source="epic") as patient:
            patient.active = True
            # Automatic save when context exits

        # Register gateway with HealthChainAPI
        app.register_gateway(fhir_gateway)
        ```
    """

    def __init__(
        self,
        base_url: str = None,
        sources: Dict[str, Union[FHIRServerInterface, str]] = None,
        prefix: str = "/fhir",
        tags: List[str] = ["FHIR"],
        use_events: bool = True,
        connection_pool_size: int = 10,
        **options,
    ):
        """
        Initialize the FHIR Gateway.

        Args:
            base_url: Base URL for FHIR server (optional if using sources)
            sources: Dictionary of named FHIR servers or connection strings
            prefix: URL prefix for API routes
            tags: OpenAPI tags
            use_events: Enable event-based processing
            connection_pool_size: Maximum size of the connection pool per source
            **options: Additional options
        """
        # Initialize as BaseGateway and APIRouter
        BaseGateway.__init__(self, use_events=use_events, **options)
        APIRouter.__init__(self, prefix=prefix, tags=tags)

        self.base_url = base_url
        self.use_events = use_events

        # Create connection pool
        self.connection_pool = FHIRConnectionPool(max_connections=connection_pool_size)

        # Store configuration
        self.sources = {}
        self._connection_strings = {}

        # Add sources if provided
        if sources:
            for name, source in sources.items():
                if isinstance(source, str):
                    self.add_source(name, source)
                else:
                    self.sources[name] = source

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
        Register routes for all handlers directly on the APIRouter.

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
                    return result
                except Exception as e:
                    logger.error(f"Error in transform handler: {str(e)}")
                    raise HTTPException(status_code=500, detail=str(e))

            return transform_handler

        # Add the route directly to the APIRouter
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
                    return result
                except Exception as e:
                    logger.error(f"Error in aggregate handler: {str(e)}")
                    raise HTTPException(status_code=500, detail=str(e))

            return aggregate_handler

        # Add the route directly to the APIRouter
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
        resource_type: str,
        operation: str,
        handler: Callable,
    ):
        """Register a custom handler for a resource operation."""
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

    def add_source(self, name: str, connection_string: str):
        """
        Add a FHIR data source using connection string.

        Format: fhir://hostname:port/path?param1=value1&param2=value2

        Examples:
            fhir://r4.smarthealthit.org
            fhir://epic.org:443/r4?auth=oauth&client_id=app&timeout=30
        """
        # Store connection string for pooling
        self._connection_strings[name] = connection_string

        # Parse the connection string for validation only
        try:
            if not connection_string.startswith("fhir://"):
                raise ValueError("Connection string must start with fhir://")

            # Parse URL for validation
            parsed = urllib.parse.urlparse(connection_string)

            # Validate that we have a valid hostname
            if not parsed.netloc:
                raise ValueError("Invalid connection string: missing hostname")

            # Store the source name - actual connections will be managed by the pool
            self.sources[name] = (
                None  # Placeholder - pool will manage actual connections
            )

            logger.info(f"Added FHIR source '{name}' with connection pooling enabled")

        except Exception as e:
            raise FHIRConnectionError(
                message=f"Failed to parse connection string: {str(e)}",
                code="INVALID_CONNECTION_STRING",
                state="08001",  # SQL state code for connection failure
            )

    def _create_server_from_connection_string(
        self, connection_string: str
    ) -> FHIRServerInterface:
        """
        Create a FHIR server instance from a connection string.

        This is used by the connection pool to create new server instances.

        Args:
            connection_string: FHIR connection string

        Returns:
            FHIRServerInterface: A new FHIR server instance
        """
        # Parse the connection string
        parsed = urllib.parse.urlparse(connection_string)

        # Extract parameters
        params = dict(urllib.parse.parse_qsl(parsed.query))

        # Create appropriate server based on parameters
        from healthchain.gateway.clients import create_fhir_server

        return create_fhir_server(
            base_url=f"https://{parsed.netloc}{parsed.path}", **params
        )

    def get_pooled_connection(self, source: str = None) -> FHIRServerInterface:
        """
        Get a pooled FHIR server connection.

        Use this method when you need direct access to a FHIR server connection
        outside of the resource_context manager. Remember to call release_pooled_connection()
        when done to return the connection to the pool.

        Args:
            source: Source name to get connection for (uses first available if None)

        Returns:
            FHIRServerInterface: A pooled FHIR server connection

        Raises:
            ValueError: If source is unknown or no connection string found
        """
        source_name = source or next(iter(self.sources.keys()))
        if source_name not in self.sources:
            raise ValueError(f"Unknown source: {source_name}")

        if source_name not in self._connection_strings:
            raise ValueError(f"No connection string found for source: {source_name}")

        connection_string = self._connection_strings[source_name]

        return self.connection_pool.get_connection(
            connection_string, self._create_server_from_connection_string
        )

    def release_pooled_connection(
        self, server: FHIRServerInterface, source: str = None
    ):
        """
        Release a pooled FHIR server connection back to the pool.

        Args:
            server: The server connection to release
            source: Source name the connection belongs to (uses first available if None)
        """
        source_name = source or next(iter(self.sources.keys()))
        if source_name in self._connection_strings:
            connection_string = self._connection_strings[source_name]
            self.connection_pool.release_connection(connection_string, server)

    @asynccontextmanager
    async def resource_context(
        self, resource_type: str, id: str = None, source: str = None
    ):
        """
        Context manager for working with FHIR resources.

        Automatically handles fetching, updating, and error handling using connection pooling.

        Args:
            resource_type: The FHIR resource type (e.g. 'Patient')
            id: Resource ID (if None, creates a new resource)
            source: Source name to use (uses first available if None)

        Yields:
            Resource: The FHIR resource object

        Raises:
            FHIRConnectionError: If connection fails
            ValueError: If resource type is invalid
        """
        # Get the source name and connection string
        source_name = source or next(iter(self.sources.keys()))
        if source_name not in self.sources:
            raise ValueError(f"Unknown source: {source_name}")

        if source_name not in self._connection_strings:
            raise ValueError(f"No connection string found for source: {source_name}")

        connection_string = self._connection_strings[source_name]

        # Get server from connection pool
        server = self.connection_pool.get_connection(
            connection_string, self._create_server_from_connection_string
        )

        resource = None
        is_new = id is None

        try:
            # Dynamically import the resource class
            import importlib

            resource_module = importlib.import_module(
                f"fhir.resources.{resource_type.lower()}"
            )
            resource_class = getattr(resource_module, resource_type)

            if is_new:
                # Create new resource
                resource = resource_class()
                logger.debug(
                    f"Created new {resource_type} resource using pooled connection"
                )
            else:
                # Fetch existing resource
                result = await server.read(f"{resource_type}/{id}")
                if result:
                    resource = resource_class(**result)
                else:
                    raise ValueError(f"Resource {resource_type}/{id} not found")
                logger.debug(f"Retrieved {resource_type}/{id} using pooled connection")

            # Emit read event if fetching existing resource
            if not is_new:
                self._emit_fhir_event("read", resource_type, id, resource)

            # Yield the resource for the context block
            yield resource

            # After the context block, save changes
            if is_new:
                result = await server.create(resource_type, resource.dict())
                if result and "id" in result:
                    resource.id = result[
                        "id"
                    ]  # Update resource with server-assigned ID
                self._emit_fhir_event("create", resource_type, resource.id, resource)
                logger.debug(
                    f"Created {resource_type} resource using pooled connection"
                )
            else:
                await server.update(resource_type, id, resource.dict())
                self._emit_fhir_event("update", resource_type, id, resource)
                logger.debug(f"Updated {resource_type}/{id} using pooled connection")

        except Exception as e:
            logger.error(f"Error in resource context: {str(e)}")
            raise FHIRConnectionError(
                message=f"Resource operation failed: {str(e)}",
                code="RESOURCE_ERROR",
                state="HY000",  # General error
            )
        finally:
            # Return the server connection to the pool
            self.connection_pool.release_connection(connection_string, server)
            logger.debug(f"Released connection for {source_name} back to pool")

    @property
    def supported_resources(self) -> List[str]:
        """Get list of supported FHIR resource types."""
        resources = set(self._resource_handlers.keys())

        # Add any other resources that might be supported through other means
        # (This could be expanded based on your implementation)

        return list(resources)

    def aggregate(self, resource_type: str):
        """Decorator for custom aggregation functions."""

        def decorator(handler: Callable):
            self._register_resource_handler(resource_type, "aggregate", handler)
            return handler

        return decorator

    def transform(self, resource_type: str):
        """Decorator for custom transformation functions."""

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

        # Add custom operations
        capabilities.extend([op for op in self._handlers.keys()])

        return capabilities

    def get_connection_pool_status(self) -> Dict[str, Any]:
        """
        Get the current status of the connection pool.

        Returns:
            Dict containing pool status information including:
            - max_connections: Maximum connections per source
            - sources: Dict of source names and their current pool sizes
            - total_pooled_connections: Total number of pooled connections
        """
        pool_status = {
            "max_connections": self.connection_pool.max_connections,
            "sources": {},
            "total_pooled_connections": 0,
        }

        for source_name, connection_string in self._connection_strings.items():
            pool_size = len(
                self.connection_pool._connections.get(connection_string, [])
            )
            pool_status["sources"][source_name] = {
                "connection_string": connection_string,
                "pooled_connections": pool_size,
            }
            pool_status["total_pooled_connections"] += pool_size

        return pool_status
