"""
HealthChainAPI - FastAPI wrapper with healthcare integration capabilities.

This module provides the main HealthChainAPI class that wraps FastAPI and manages
healthcare-specific gateways, routes, middleware, and capabilities.
"""

import logging
import importlib
import inspect
import os
import signal

from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from termcolor import colored

from typing import Dict, Optional, Type, Union

from healthchain.gateway.core.base import BaseGateway, BaseProtocolHandler
from healthchain.gateway.events.dispatcher import EventDispatcher
from healthchain.gateway.api.dependencies import get_app

logger = logging.getLogger(__name__)


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
        cds_service = CDSHooksService()
        note_service = NoteReaderService()

        # Register with the API
        app.register_gateway(fhir_gateway)

        app.register_service(cds_service)
        app.register_service(note_service)

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
            title: API title
            description: API description
            version: API version
            enable_cors: Enable CORS middleware
            enable_events: Enable event dispatching
            event_dispatcher: Optional custom event dispatcher
            **kwargs: Additional FastAPI configuration
        """
        super().__init__(
            title=title, description=description, version=version, **kwargs
        )

        # Gateway and service registries
        self.gateways = {}
        self.services = {}
        self.gateway_endpoints = {}
        self.service_endpoints = {}

        # Event system setup
        self.enable_events = enable_events
        self.event_dispatcher = None

        if enable_events:
            if event_dispatcher:
                self.event_dispatcher = event_dispatcher
            else:
                from healthchain.gateway.events.dispatcher import EventDispatcher

                self.event_dispatcher = EventDispatcher()

            # Initialize the event dispatcher
            self.event_dispatcher.init_app(self)

        # Setup middleware
        if enable_cors:
            self.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # Can be configured from settings
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Add global exception handlers
        self.add_exception_handler(
            RequestValidationError, self._validation_exception_handler
        )
        self.add_exception_handler(HTTPException, self._http_exception_handler)
        self.add_exception_handler(Exception, self._general_exception_handler)

        # Add default routes
        self._add_default_routes()

        # Register self as a dependency for get_app
        self.dependency_overrides[get_app] = lambda: self

        # Add a shutdown route
        shutdown_router = APIRouter()
        shutdown_router.add_api_route(
            "/shutdown", self._shutdown, methods=["GET"], include_in_schema=False
        )
        self.include_router(shutdown_router)

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

    def get_service(self, service_name: str) -> Optional[BaseProtocolHandler]:
        """Get a specific service by name.

        Args:
            service_name: The name of the service

        Returns:
            The service instance or None if not found
        """
        return self.services.get(service_name)

    def get_all_services(self) -> Dict[str, BaseProtocolHandler]:
        """Get all registered services.

        Returns:
            Dictionary of all registered services
        """
        return self.services

    def _register_component(
        self,
        component: Union[Type, object],
        component_type: str,
        path: Optional[str] = None,
        use_events: Optional[bool] = None,
        **options,
    ) -> None:
        """
        Generic method to register gateways or services.

        Args:
            component: The component class or instance to register
            component_type: Either 'gateway' or 'service'
            path: Optional override for the component's mount path
            use_events: Whether to enable events for this component
            **options: Options to pass to the constructor
        """
        try:
            # Determine if events should be used
            component_use_events = (
                self.enable_events if use_events is None else use_events
            )

            # Get the appropriate registry and base class
            if component_type == "gateway":
                registry = self.gateways
                # endpoints_registry = self.gateway_endpoints
                base_class = BaseGateway
            else:  # service
                registry = self.services
                # endpoints_registry = self.service_endpoints
                base_class = BaseProtocolHandler

            # Check if instance is already provided
            if isinstance(component, base_class):
                component_instance = component
                component_name = component.__class__.__name__
            else:
                # Create a new instance
                if "use_events" not in options:
                    options["use_events"] = component_use_events
                component_instance = component(**options)
                component_name = component.__class__.__name__

            # Add to internal registry
            registry[component_name] = component_instance

            # Provide event dispatcher if events are enabled
            if (
                component_use_events
                and self.event_dispatcher
                and hasattr(component_instance, "events")
                and hasattr(component_instance.events, "set_dispatcher")
            ):
                component_instance.events.set_dispatcher(self.event_dispatcher)

            # Add routes to FastAPI app
            if component_type == "gateway":
                self._add_gateway_routes(component_instance, path)
            else:
                self._add_service_routes(component_instance, path)

        except Exception as e:
            logger.error(
                f"Failed to register {component_type} {component.__name__ if hasattr(component, '__name__') else component.__class__.__name__}: {str(e)}"
            )
            raise

    def register_gateway(
        self,
        gateway: Union[Type[BaseGateway], BaseGateway],
        path: Optional[str] = None,
        use_events: Optional[bool] = None,
        **options,
    ) -> None:
        """Register a gateway with the API and mount its endpoints."""
        self._register_component(gateway, "gateway", path, use_events, **options)

    def register_service(
        self,
        service: Union[Type[BaseProtocolHandler], BaseProtocolHandler],
        path: Optional[str] = None,
        use_events: Optional[bool] = None,
        **options,
    ) -> None:
        """Register a service with the API and mount its endpoints."""
        self._register_component(service, "service", path, use_events, **options)

    def _add_gateway_routes(
        self, gateway: BaseGateway, path: Optional[str] = None
    ) -> None:
        """Add gateway routes to the FastAPI app.

        Args:
            gateway: The gateway to add routes for
            path: Optional override for the mount path
        """
        gateway_name = gateway.__class__.__name__
        self.gateway_endpoints[gateway_name] = set()

        if not isinstance(gateway, APIRouter):
            logger.warning(
                f"Gateway {gateway_name} is not an APIRouter and cannot be registered"
            )
            return

        # Use provided path or gateway's prefix
        mount_path = path or gateway.prefix
        if mount_path:
            gateway.prefix = mount_path

        self.include_router(gateway)

        if not hasattr(gateway, "routes"):
            logger.debug(f"Registered {gateway_name} as router (routes unknown)")
            return

        for route in gateway.routes:
            for method in route.methods:
                endpoint = f"{method}:{route.path}"
                self.gateway_endpoints[gateway_name].add(endpoint)
                logger.debug(
                    f"Registered {method} route {route.path} from {gateway_name} router"
                )

    def _add_service_routes(
        self, service: BaseProtocolHandler, path: Optional[str] = None
    ) -> None:
        """
        Add service routes to the FastAPI app.

        Args:
            service: The service to add routes for
            path: Optional override for the mount path
        """
        service_name = service.__class__.__name__
        self.service_endpoints[service_name] = set()

        # Case 1: Services with get_routes implementation (CDS Hooks, etc.)
        if hasattr(service, "get_routes") and callable(service.get_routes):
            routes = service.get_routes(path)
            if routes:
                for route_path, methods, handler, kwargs in routes:
                    for method in methods:
                        self.add_api_route(
                            path=route_path,
                            endpoint=handler,
                            methods=[method],
                            **kwargs,
                        )
                        self.service_endpoints[service_name].add(
                            f"{method}:{route_path}"
                        )
                        logger.debug(
                            f"Registered {method} route {route_path} for {service_name}"
                        )

        # Case 2: WSGI services (like SOAP)
        if hasattr(service, "create_wsgi_app") and callable(service.create_wsgi_app):
            # For SOAP/WSGI services
            wsgi_app = service.create_wsgi_app()

            # Determine mount path
            mount_path = path
            if mount_path is None and hasattr(service, "config"):
                # Try to get the default path from the service config
                mount_path = getattr(service.config, "default_mount_path", None)
                if not mount_path:
                    mount_path = getattr(service.config, "base_path", None)

            if not mount_path:
                # Fallback path based on service name
                mount_path = f"/{service_name.lower().replace('service', '').replace('gateway', '')}"

            # Mount the WSGI app
            self.mount(mount_path, WSGIMiddleware(wsgi_app))
            self.service_endpoints[service_name].add(f"WSGI:{mount_path}")
            logger.debug(f"Registered WSGI service {service_name} at {mount_path}")

        elif not (
            hasattr(service, "get_routes")
            and callable(service.get_routes)
            and service.get_routes(path)
        ):
            logger.warning(f"Service {service_name} does not provide any routes")

    def register_router(
        self, router: Union[APIRouter, Type, str, list], **options
    ) -> None:
        """
        Register one or more routers with the API.

        Args:
            router: The router(s) to register (can be an instance, class, import path, or list of any of these)
            **options: Options to pass to the router constructor or include_router
        """
        try:
            # Handle list of routers
            if isinstance(router, list):
                for r in router:
                    self.register_router(r, **options)
                return

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
                "services": list(self.services.keys()),
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

            service_info = {}
            for name, service in self.services.items():
                # Try to get metadata if available
                if hasattr(service, "get_metadata") and callable(service.get_metadata):
                    service_info[name] = service.get_metadata()
                else:
                    service_info[name] = {
                        "type": name,
                        "endpoints": list(self.service_endpoints.get(name, set())),
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
                "services": service_info,
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

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Lifecycle manager for the application."""
        self._startup()
        yield
        self._shutdown()

    def _startup(self) -> None:
        """Display startup information and log registered endpoints."""
        healthchain_ascii = r"""

    __  __           ____  __    ________          _
   / / / /__  ____ _/ / /_/ /_  / ____/ /_  ____ _(_)___
  / /_/ / _ \/ __ `/ / __/ __ \/ /   / __ \/ __ `/ / __ \
 / __  /  __/ /_/ / / /_/ / / / /___/ / / / /_/ / / / / /
/_/ /_/\___/\__,_/_/\__/_/ /_/\____/_/ /_/\__,_/_/_/ /_/

"""  # noqa: E501

        colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]
        for i, line in enumerate(healthchain_ascii.split("\n")):
            color = colors[i % len(colors)]
            print(colored(line, color))

        # Log registered gateways and endpoints
        for name, gateway in self.gateways.items():
            endpoints = self.gateway_endpoints.get(name, set())
            for endpoint in endpoints:
                print(f"{colored('HEALTHCHAIN', 'green')}: {endpoint}")

        print(
            f"{colored('HEALTHCHAIN', 'green')}: See more details at {colored(self.docs_url, 'magenta')}"
        )

    def _shutdown(self):
        """
        Shuts down server by sending a SIGTERM signal.
        """
        os.kill(os.getpid(), signal.SIGTERM)
        return JSONResponse(content={"message": "Server is shutting down..."})


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
