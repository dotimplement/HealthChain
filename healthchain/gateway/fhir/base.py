import logging
import inspect
import warnings

from fastapi import Depends, HTTPException, Path, Query
from datetime import datetime
from typing import Any, Callable, Dict, List, Type, TypeVar, Optional
from fastapi.responses import JSONResponse

from fhir.resources.capabilitystatement import CapabilityStatement
from fhir.resources.resource import Resource

from healthchain.gateway.clients.fhir.base import FHIRServerInterface
from healthchain.gateway.base import BaseGateway


logger = logging.getLogger(__name__)


# Type variable for FHIR Resource
T = TypeVar("T", bound=Resource)


class FHIRResponse(JSONResponse):
    """
    Custom response class for FHIR resources.

    This sets the correct content-type header for FHIR resources.
    """

    media_type = "application/fhir+json"


class BaseFHIRGateway(BaseGateway):
    """
    Base FHIR Gateway with shared functionality.

    Contains all common FHIR gateway logic including routing, decorators,
    capability statements, and resource management.

    Subclasses implement sync vs async specific methods.
    """

    def __init__(
        self,
        sources: Dict[str, FHIRServerInterface] = None,
        prefix: str = "/fhir",
        tags: List[str] = ["FHIR"],
        use_events: bool = False,
        **options,
    ):
        """Initialize the Base FHIR Gateway."""
        # Initialize as BaseGateway (which includes APIRouter)
        super().__init__(use_events=use_events, prefix=prefix, tags=tags, **options)

        self.use_events = use_events

        # Initialize connection manager (subclasses will set appropriate type)
        self.connection_manager = None

        # Store sources for initialization
        self._initial_sources = sources

        # Handlers for resource operations
        self._resource_handlers: Dict[str, Dict[str, Callable]] = {}

        # Register base routes only (metadata endpoint)
        self._register_base_routes()

    def _initialize_connection_manager(self):
        """Initialize connection manager with sources. Called by subclasses."""
        # Add initial sources if provided
        if self._initial_sources:
            for name, source in self._initial_sources.items():
                if isinstance(source, str):
                    self.connection_manager.add_source(name, source)
                else:
                    self.connection_manager.sources[name] = source

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
            fhir: "BaseFHIRGateway" = Depends(get_self_gateway),
        ):
            """Return the FHIR capability statement for this gateway's services.

            Includes both custom transform/aggregate operations (via REST endpoints)
            and standard FHIR CRUD operations (via Python gateway methods).
            """
            return fhir.build_capability_statement().model_dump(exclude_none=True)

        # Gateway status endpoint - returns operational metadata
        @self.get("/status", response_class=JSONResponse)
        def gateway_status(
            fhir: "BaseFHIRGateway" = Depends(get_self_gateway),
        ):
            """Return operational status and metadata for this gateway.

            Includes information about supported FHIR CRUD operations,
            custom transform/aggregate operations, and connected sources.
            """
            return fhir.get_gateway_status()

    def build_capability_statement(self) -> CapabilityStatement:
        """
        Build a FHIR CapabilityStatement for this gateway's value-add services.

        Returns detailed capability information including registered transform/aggregate
        handlers, available FHIR sources, and supported operations.

        Returns:
            CapabilityStatement: FHIR-compliant capability statement for gateway operations
        """
        # Build resource entries based on registered handlers
        resources = []
        for resource_type, operations in self._resource_handlers.items():
            interactions = []
            operation_details = []

            # Add supported interactions based on registered handlers
            for operation in operations:
                if operation == "transform":
                    interactions.append(
                        {
                            "code": "read",
                            "documentation": "Custom transformation via REST endpoint",
                        }
                    )
                    operation_details.append(
                        "Transform: Custom resource transformation"
                    )
                elif operation == "aggregate":
                    interactions.append(
                        {
                            "code": "search-type",
                            "documentation": "Multi-source aggregation via REST endpoint",
                        }
                    )
                    operation_details.append("Aggregate: Multi-source data aggregation")

            if interactions:
                resource_name = self._get_resource_name(resource_type)
                documentation = f"Gateway provides {', '.join(operation_details)} for {resource_name}"
                resources.append(
                    {
                        "type": resource_name,
                        "interaction": interactions,
                        "documentation": documentation,
                    }
                )

        # Add available FHIR sources information
        sources_info = []
        if self.connection_manager and hasattr(self.connection_manager, "sources"):
            for source_name in self.connection_manager.sources.keys():
                sources_info.append(f"Source: {source_name}")

        # Enhanced documentation with examples
        sources_list = (
            ", ".join(self.connection_manager.sources.keys())
            if self.connection_manager and hasattr(self.connection_manager, "sources")
            else "None configured"
        )
        rest_documentation = (
            "HealthChain FHIR Gateway provides transformation and aggregation services. "
            f"Gateway also provides standard FHIR CRUD operations (create, read, update, delete, search) to connected FHIR servers via Python API. "
            f"Available sources: {sources_list}. "
            "Use /status endpoint for operational details."
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
            "fhirVersion": "5.0.0",
            "format": ["application/fhir+json"],
            "rest": [
                {
                    "mode": "server",
                    "documentation": rest_documentation,
                    "resource": resources,
                }
            ],
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

        Enhanced with detailed FHIR operation discovery information including
        both standard CRUD operations and custom transform/aggregate operations.

        Returns:
            Dict containing gateway operational status and metadata
        """
        # Get available operations with examples
        available_operations = {}
        for resource_type, operations in self._resource_handlers.items():
            resource_name = self._get_resource_name(resource_type)
            operation_list = []

            for operation in operations:
                if operation == "transform":
                    operation_list.append(
                        {
                            "type": "transform",
                            "endpoint": f"/transform/{resource_name}/{{id}}",
                            "description": f"Transform {resource_name} with custom logic",
                            "method": "GET",
                            "parameters": ["id", "source (optional)"],
                        }
                    )
                elif operation == "aggregate":
                    operation_list.append(
                        {
                            "type": "aggregate",
                            "endpoint": f"/aggregate/{resource_name}",
                            "description": f"Aggregate {resource_name} from multiple sources",
                            "method": "GET",
                            "parameters": ["id (optional)", "sources (optional)"],
                        }
                    )

            if operation_list:
                available_operations[resource_name] = operation_list

        status = {
            "gateway_type": self.__class__.__name__,
            "version": "1.0.0",  # TODO: Extract from package
            "status": "active",
            "timestamp": datetime.now().isoformat() + "Z",
            "sources": {
                "count": len(self.connection_manager.sources)
                if self.connection_manager
                and hasattr(self.connection_manager, "sources")
                else 0,
                "names": list(self.connection_manager.sources.keys())
                if self.connection_manager
                and hasattr(self.connection_manager, "sources")
                else [],
            },
            "connection_pool": self.connection_manager.get_status()
            if self.connection_manager
            else {"status": "not_initialized"},
            "supported_operations": available_operations,
            "discovery_endpoints": {
                "/metadata": "FHIR CapabilityStatement with supported operations",
                "/status": "Gateway operational status and available operations",
                "/docs": "OpenAPI documentation for all endpoints",
            },
            "events": {
                "enabled": self.use_events,
                "dispatcher_configured": hasattr(self, "events")
                and self.events
                and self.events.dispatcher is not None,
                "event_type": "async"
                if self.__class__.__name__ == "AsyncFHIRGateway"
                else "logging_only",
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

        def _execute_handler(fhir: "BaseFHIRGateway", *args) -> Any:
            """Common handler execution logic with error handling."""
            try:
                handler_func = fhir._resource_handlers[resource_type][operation]
                result = handler_func(*args)

                # Serialize FHIR resources excluding None values
                if isinstance(result, Resource):
                    return result.model_dump(exclude_none=True)
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
                fhir: "BaseFHIRGateway" = Depends(get_self_gateway),
            ):
                """Transform a resource with registered handler."""
                return _execute_handler(fhir, id, source)

        elif operation == "aggregate":

            async def handler(
                id: Optional[str] = Query(None, description="ID to aggregate data for"),
                sources: Optional[List[str]] = Query(
                    None, description="List of source names to query"
                ),
                fhir: "BaseFHIRGateway" = Depends(get_self_gateway),
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

    def aggregate(self, resource_type: Type[Resource]):
        """
        Decorator for custom aggregation functions. Can return the same resource type or a bundle of resources.

        Args:
            resource_type: The FHIR resource type class that this handler aggregates

        Example:
            @fhir_gateway.aggregate(Patient)
            def aggregate_patients(id: str = None, sources: List[str] = None) -> Patient | Bundle:
                # Handler implementation
                pass
        """

        def decorator(handler: Callable):
            self._register_resource_handler(resource_type, "aggregate", handler)
            return handler

        return decorator

    def transform(self, resource_type: Type[Resource]):
        """
        Decorator for custom transformation functions. Must return the same resource type.

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
