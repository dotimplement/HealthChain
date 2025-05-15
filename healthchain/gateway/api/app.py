"""
HealthChainAPI - FastAPI wrapper with healthcare integration capabilities.

This module provides the main HealthChainAPI class that wraps FastAPI and manages
healthcare-specific gateways, routes, middleware, and capabilities.
"""

import logging
import importlib
import inspect

from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from typing import Dict, Optional, Type, Union, Set, ForwardRef

from healthchain.gateway.core.base import BaseGateway
from healthchain.gateway.events.dispatcher import EventDispatcher
from healthchain.gateway.api.dependencies import get_app

logger = logging.getLogger(__name__)


# Forward reference for type hints
HealthChainAPIRef = ForwardRef("HealthChainAPI")


class HealthChainAPI(FastAPI):
    """
    HealthChainAPI wraps FastAPI to provide healthcare-specific integrations.

    This class extends FastAPI to provide additional capabilities for:
    - Managing healthcare gateways (FHIR, CDA, CDS Hooks, SOAP, etc.)
    - Routing and transforming healthcare data
    - Handling healthcare-specific authentication and authorization
    - Managing healthcare-specific configurations
    - Providing capability statements and gateway discovery
    - Event dispatch for healthcare events

    Example:
        ```python
        # Create the API
        app = HealthChainAPI()

        # Create and register gateways
        fhir_gateway = FHIRGateway()
        cds_gateway = CDSHooksGateway()
        note_gateway = NoteReaderGateway()

        # Register with the API
        app.register_gateway(fhir_gateway)
        app.register_gateway(cds_gateway)
        app.register_gateway(note_gateway)

        # Run the app with uvicorn
        uvicorn.run(app)
        ```
    """

    def __init__(
        self,
        title: str = "HealthChain API",
        description: str = "Healthcare Integration API",
        version: str = "1.0.0",
        enable_cors: bool = True,
        enable_events: bool = True,
        event_dispatcher: Optional[EventDispatcher] = None,
        **kwargs,
    ):
        """
        Initialize the HealthChainAPI application.

        Args:
            title: API title for documentation
            description: API description for documentation
            version: API version
            enable_cors: Whether to enable CORS middleware
            enable_events: Whether to enable event dispatching functionality
            event_dispatcher: Optional event dispatcher to use (for testing/DI)
            **kwargs: Additional keyword arguments to pass to FastAPI
        """
        super().__init__(
            title=title, description=description, version=version, **kwargs
        )

        self.gateways: Dict[str, BaseGateway] = {}
        self.gateway_endpoints: Dict[str, Set[str]] = {}
        self.enable_events = enable_events

        # Initialize event dispatcher if events are enabled
        if self.enable_events:
            self.event_dispatcher = event_dispatcher or EventDispatcher()
            if not event_dispatcher:  # Only initialize if we created it
                self.event_dispatcher.init_app(self)
        else:
            self.event_dispatcher = None

        # Add default middleware
        if enable_cors:
            self.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # Can be configured from settings
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Add exception handlers
        self.add_exception_handler(
            RequestValidationError, self._validation_exception_handler
        )
        self.add_exception_handler(HTTPException, self._http_exception_handler)
        self.add_exception_handler(Exception, self._general_exception_handler)

        # Add default routes
        self._add_default_routes()

        # Register self as a dependency for get_app
        self.dependency_overrides[get_app] = lambda: self

    def get_event_dispatcher(self) -> Optional[EventDispatcher]:
        """Get the event dispatcher instance.

        This method is used for dependency injection in route handlers.

        Returns:
            The application's event dispatcher, or None if events are disabled
        """
        return self.event_dispatcher

    def get_gateway(self, gateway_name: str) -> Optional[BaseGateway]:
        """Get a specific gateway by name.

        Args:
            gateway_name: The name of the gateway to retrieve

        Returns:
            The gateway instance or None if not found
        """
        return self.gateways.get(gateway_name)

    def get_all_gateways(self) -> Dict[str, BaseGateway]:
        """Get all registered gateways.

        Returns:
            Dictionary of all registered gateways
        """
        return self.gateways

    def register_gateway(
        self,
        gateway: Union[Type[BaseGateway], BaseGateway],
        path: Optional[str] = None,
        use_events: Optional[bool] = None,
        **options,
    ) -> None:
        """
        Register a gateway with the API and mount its endpoints.

        Args:
            gateway: The gateway class or instance to register
            path: Optional override for the gateway's mount path
            use_events: Whether to enable events for this gateway (defaults to app setting)
            **options: Options to pass to the constructor
        """
        try:
            # Determine if events should be used for this gateway
            gateway_use_events = (
                self.enable_events if use_events is None else use_events
            )

            # Check if instance is already provided
            if isinstance(gateway, BaseGateway):
                gateway_instance = gateway
                gateway_name = gateway.__class__.__name__
            else:
                # Create a new instance
                if "use_events" not in options:
                    options["use_events"] = gateway_use_events
                gateway_instance = gateway(**options)
                gateway_name = gateway.__class__.__name__

            # Add to internal gateway registry
            self.gateways[gateway_name] = gateway_instance

            # Provide event dispatcher to gateway if events are enabled
            if (
                gateway_use_events
                and self.event_dispatcher
                and hasattr(gateway_instance, "set_event_dispatcher")
                and callable(gateway_instance.set_event_dispatcher)
            ):
                gateway_instance.set_event_dispatcher(self.event_dispatcher)

            # Add gateway routes to FastAPI app
            self._add_gateway_routes(gateway_instance, path)

        except Exception as e:
            logger.error(
                f"Failed to register gateway {gateway.__name__ if hasattr(gateway, '__name__') else gateway.__class__.__name__}: {str(e)}"
            )
            raise

    def _add_gateway_routes(
        self, gateway: BaseGateway, path: Optional[str] = None
    ) -> None:
        """
        Add gateway routes to the FastAPI app.

        Args:
            gateway: The gateway to add routes for
            path: Optional override for the mount path
        """
        gateway_name = gateway.__class__.__name__
        self.gateway_endpoints[gateway_name] = set()

        # Case 1: Gateways with get_routes implementation
        if hasattr(gateway, "get_routes") and callable(gateway.get_routes):
            routes = gateway.get_routes(path)
            if routes:
                for route_path, methods, handler, kwargs in routes:
                    for method in methods:
                        self.add_api_route(
                            path=route_path,
                            endpoint=handler,
                            methods=[method],
                            **kwargs,
                        )
                        self.gateway_endpoints[gateway_name].add(
                            f"{method}:{route_path}"
                        )
                        logger.info(
                            f"Registered {method} route {route_path} for {gateway_name}"
                        )

        # Case 2: WSGI gateways (like SOAP)
        if hasattr(gateway, "create_wsgi_app") and callable(gateway.create_wsgi_app):
            # For SOAP/WSGI gateways
            wsgi_app = gateway.create_wsgi_app()

            # Determine mount path
            mount_path = path
            if mount_path is None and hasattr(gateway, "config"):
                # Try to get the default path from the gateway config
                mount_path = getattr(gateway.config, "default_mount_path", None)
                if not mount_path:
                    mount_path = getattr(gateway.config, "base_path", None)

            if not mount_path:
                # Fallback path based on gateway name
                mount_path = f"/{gateway_name.lower().replace('gateway', '')}"

            # Mount the WSGI app
            self.mount(mount_path, WSGIMiddleware(wsgi_app))
            self.gateway_endpoints[gateway_name].add(f"WSGI:{mount_path}")
            logger.info(f"Registered WSGI gateway {gateway_name} at {mount_path}")

        # Case 3: Gateway instances that are also APIRouters (like FHIRGateway)
        elif isinstance(gateway, APIRouter):
            # Include the router
            self.include_router(gateway)
            if hasattr(gateway, "routes"):
                for route in gateway.routes:
                    for method in route.methods:
                        self.gateway_endpoints[gateway_name].add(
                            f"{method}:{route.path}"
                        )
                        logger.info(
                            f"Registered {method} route {route.path} from {gateway_name} router"
                        )
            else:
                logger.info(f"Registered {gateway_name} as router (routes unknown)")

        elif not (
            hasattr(gateway, "get_routes")
            and callable(gateway.get_routes)
            and gateway.get_routes(path)
        ):
            logger.warning(f"Gateway {gateway_name} does not provide any routes")

    def register_router(self, router: Union[APIRouter, Type, str], **options) -> None:
        """
        Register a router with the API.

        Args:
            router: The router to register (can be an instance, class, or import path)
            **options: Options to pass to the router constructor or include_router
        """
        try:
            # Case 1: Direct APIRouter instance
            if isinstance(router, APIRouter):
                self.include_router(router, **options)
                return

            # Case 2: Router class that needs instantiation
            if inspect.isclass(router):
                instance = router(**options)
                if not isinstance(instance, APIRouter):
                    raise TypeError(
                        f"Expected APIRouter instance, got {type(instance)}"
                    )
                self.include_router(instance)
                return

            # Case 3: Import path as string
            if isinstance(router, str):
                module_path, class_name = router.rsplit(".", 1)
                module = importlib.import_module(module_path)
                router_class = getattr(module, class_name)
                instance = router_class(**options)
                if not isinstance(instance, APIRouter):
                    raise TypeError(
                        f"Expected APIRouter instance, got {type(instance)}"
                    )
                self.include_router(instance)
                return

            raise TypeError(f"Unsupported router type: {type(router)}")

        except Exception as e:
            router_name = getattr(router, "__name__", str(router))
            logger.error(f"Failed to register router {router_name}: {str(e)}")
            raise

    def _add_default_routes(self) -> None:
        """Add default routes for the API."""

        @self.get("/")
        async def root():
            """Root endpoint providing basic API information."""
            return {
                "name": self.title,
                "version": self.version,
                "description": self.description,
                "gateways": list(self.gateways.keys()),
            }

        @self.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy"}

        @self.get("/metadata")
        async def metadata():
            """Provide capability statement for the API."""
            gateway_info = {}
            for name, gateway in self.gateways.items():
                # Try to get metadata if available
                if hasattr(gateway, "get_metadata") and callable(gateway.get_metadata):
                    gateway_info[name] = gateway.get_metadata()
                else:
                    gateway_info[name] = {
                        "type": name,
                        "endpoints": list(self.gateway_endpoints.get(name, set())),
                    }

            return {
                "resourceType": "CapabilityStatement",
                "status": "active",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "kind": "instance",
                "software": {
                    "name": self.title,
                    "version": self.version,
                },
                "implementation": {
                    "description": self.description,
                    "url": "/",
                },
                "gateways": gateway_info,
            }

    async def _validation_exception_handler(
        self, request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation exceptions."""
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": exc.body},
        )

    async def _http_exception_handler(
        self, request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    async def _general_exception_handler(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle general exceptions."""
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


def create_app(
    config: Optional[Dict] = None,
    enable_events: bool = True,
    event_dispatcher: Optional[EventDispatcher] = None,
) -> HealthChainAPI:
    """
    Factory function to create a new HealthChainAPI application.

    This function provides a simple way to create a HealthChainAPI application
    with standard middleware and basic configuration. It's useful for quickly
    bootstrapping an application with sensible defaults.

    Args:
        config: Optional configuration dictionary
        enable_events: Whether to enable event dispatching functionality
        event_dispatcher: Optional event dispatcher to use (for testing/DI)

    Returns:
        Configured HealthChainAPI instance
    """
    # Setup basic application config
    app_config = {
        "title": "HealthChain API",
        "description": "Healthcare Integration API",
        "version": "0.1.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "enable_events": enable_events,
        "event_dispatcher": event_dispatcher,
    }

    # Override with user config if provided
    if config:
        app_config.update(config)

    # Create application
    app = HealthChainAPI(**app_config)

    return app
