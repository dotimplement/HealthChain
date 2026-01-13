"""
HealthChainAPI - FastAPI wrapper with healthcare integration capabilities.

This module provides the main HealthChainAPI class that wraps FastAPI and manages
healthcare-specific gateways, routes, middleware, and capabilities.
"""

import logging

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from termcolor import colored

from typing import Dict, Optional, Type, Union

from healthchain.gateway.base import BaseGateway, BaseProtocolHandler
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
            title=title,
            description=description,
            version=version,
            lifespan=self._lifespan,
            **kwargs,
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

        # Add global exception handler
        self.add_exception_handler(Exception, self._exception_handler)

        # Add default routes
        self._add_default_routes()

        # Register self as a dependency for get_app
        self.dependency_overrides[get_app] = lambda: self

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """
        Handle application lifespan events (startup and shutdown).
        """
        await self._startup()
        yield
        await self._shutdown()

    def get_event_dispatcher(self) -> Optional[EventDispatcher]:
        """Get the event dispatcher instance.

        This method is used for dependency injection in route handlers.

        Returns:
            The application's event dispatcher, or None if events are disabled
        """
        return self.event_dispatcher

    def _register_component(
        self,
        component: Union[Type, object],
        component_type: str,
        path: Optional[str] = None,
        use_events: Optional[bool] = None,
        **options,
    ) -> None:
        """Register a healthcare component (gateway or service)."""

        use_events = use_events if use_events is not None else self.enable_events
        registry, endpoints_registry, base_class = self._get_component_config(
            component_type
        )

        component_instance = self._get_component_instance(
            component, base_class, use_events, **options
        )

        registry[component_instance.__class__.__name__] = component_instance

        self._get_component_events(component_instance, use_events)
        self._add_component_routes(
            component_instance, component_type, endpoints_registry, path
        )

    def _get_component_config(self, component_type: str) -> tuple:
        """Get the appropriate registries and base class for a component type."""
        if component_type == "gateway":
            return self.gateways, self.gateway_endpoints, BaseGateway
        else:  # service
            return self.services, self.service_endpoints, BaseProtocolHandler

    def _get_component_instance(
        self,
        component: Union[Type, object],
        base_class: Type,
        use_events: bool,
        **options,
    ) -> object:
        """Create or validate a component instance and return it with its name."""
        if isinstance(component, base_class):
            # Already an instance
            component_instance = component
        else:
            # Create a new instance from the class
            if "use_events" not in options:
                options["use_events"] = use_events
            component_instance = component(**options)

        return component_instance

    def _get_component_events(
        self, component_instance: object, use_events: bool
    ) -> None:
        """Connect the event dispatcher to a component if events are enabled."""
        if (
            use_events
            and self.event_dispatcher
            and hasattr(component_instance, "events")
            and hasattr(component_instance.events, "set_dispatcher")
        ):
            component_instance.events.set_dispatcher(self.event_dispatcher)

    def _add_component_routes(
        self,
        component: Union[BaseGateway, BaseProtocolHandler],
        component_type: str,
        endpoints_registry: Dict[str, set],
        path: Optional[str] = None,
    ) -> None:
        """Add routes for a component."""

        component_name = component.__class__.__name__
        endpoints_registry[component_name] = set()

        # Case 1: APIRouter-based components (gateways and CDSHooksService)
        if isinstance(component, APIRouter):
            self._register_api_router(
                component, component_name, endpoints_registry, path
            )
            return

        # Case 2: WSGI services (like NoteReaderService) - only for services
        if (
            component_type == "service"
            and hasattr(component, "create_fastapi_router")
            and callable(component.create_fastapi_router)
        ):
            self._register_mounted_service(
                component, component_name, endpoints_registry, path
            )
            return

        # Case 3: Unsupported patterns
        if component_type == "gateway":
            logger.warning(
                f"Gateway {component_name} is not an APIRouter and cannot be registered"
            )
        else:
            logger.warning(
                f"Service {component_name} does not implement APIRouter or WSGI patterns. "
                f"Services must either inherit from APIRouter or implement create_fastapi_router()."
            )

    def _register_api_router(
        self,
        router: APIRouter,
        component_name: str,
        endpoints_registry: Dict[str, set],
        path: Optional[str] = None,
    ) -> None:
        """Register an APIRouter component."""
        mount_path = path or router.prefix
        if path:
            router.prefix = mount_path

        self.include_router(router)

        if hasattr(router, "routes"):
            for route in router.routes:
                for method in route.methods:
                    endpoint = f"{method}:{route.path}"
                    endpoints_registry[component_name].add(endpoint)
                    logger.debug(
                        f"Registered {method} route {route.path} from {component_name} router"
                    )
        else:
            logger.debug(f"Registered {component_name} as router (routes unknown)")

    def _register_mounted_service(  # Renamed from _register_wsgi_service
        self,
        service: BaseProtocolHandler,
        service_name: str,
        endpoints_registry: Dict[str, set],
        path: Optional[str] = None,
    ) -> None:
        """Register a service with a custom router."""
        router_or_app = service.create_fastapi_router()

        mount_path = (
            path
            or getattr(service.config, "default_mount_path", None)
            or getattr(service.config, "base_path", None)
            or f"/{service_name.lower().replace('service', '').replace('gateway', '')}"
        )

        logger.debug(f"🔧 Registering {service_name} at: {mount_path}")
        logger.debug(f"   Router type: {type(router_or_app)}")

        # Use include_router for APIRouter instances
        if isinstance(router_or_app, APIRouter):
            if hasattr(router_or_app, "routes"):
                logger.debug(f"   Routes in router: {len(router_or_app.routes)}")
                for route in router_or_app.routes:
                    if hasattr(route, "methods") and hasattr(route, "path"):
                        logger.info(f"     - {route.methods} {route.path}")

            self.include_router(router_or_app, prefix=mount_path)
            endpoints_registry[service_name].add(f"INCLUDED:{mount_path}")
            logger.info(f"✅ Included router {service_name} at {mount_path}")
        else:
            # For FastAPI apps, use mount
            self.mount(mount_path, router_or_app)
            endpoints_registry[service_name].add(f"MOUNTED:{mount_path}")
            logger.info(f"✅ Mounted app {service_name} at {mount_path}")

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

            def get_component_info(components, endpoints_registry):
                """Helper function to get metadata for components."""
                info = {}
                for name, component in components.items():
                    if hasattr(component, "get_metadata") and callable(
                        component.get_metadata
                    ):
                        info[name] = component.get_metadata()
                    else:
                        info[name] = {
                            "type": name,
                            "endpoints": list(endpoints_registry.get(name, set())),
                        }
                return info

            gateway_info = get_component_info(self.gateways, self.gateway_endpoints)
            service_info = get_component_info(self.services, self.service_endpoints)

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

    async def _exception_handler(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        """Unified exception handler for all types of exceptions."""
        if isinstance(exc, RequestValidationError):
            return JSONResponse(
                status_code=422,
                content={"detail": exc.errors(), "body": exc.body},
            )
        elif isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )
        else:
            logger.exception("Unhandled exception", exc_info=exc)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

    async def _startup(self) -> None:
        """Display startup information and initialize components."""
        # Display banner
        banner = r"""
    __  __           ____  __    ________          _
   / / / /__  ____ _/ / /_/ /_  / ____/ /_  ____ _(_)___
  / /_/ / _ \/ __ `/ / __/ __ \/ /   / __ \/ __ `/ / __ \
 / __  /  __/ /_/ / / /_/ / / / /___/ / / / /_/ / / / / /
/_/ /_/\___/\__,_/_/\__/_/ /_/\____/_/ /_/\__,_/_/_/ /_/
"""
        colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]
        for i, line in enumerate(banner.split("\n")):
            print(colored(line, colors[i % len(colors)]))

        # Log startup info
        logger.info(f"🚀 Starting {self.title} v{self.version}")
        logger.info(f"Gateways: {list(self.gateways.keys())}")
        logger.info(f"Services: {list(self.services.keys())}")

        # Initialize components
        for name, component in {**self.gateways, **self.services}.items():
            if hasattr(component, "startup") and callable(component.startup):
                try:
                    await component.startup()
                    logger.debug(f"Initialized: {name}")
                except Exception as e:
                    logger.warning(f"Failed to initialize {name}: {e}")

        logger.info(f"📖 Docs: {self.docs_url}")

    async def _shutdown(self) -> None:
        """Handle graceful shutdown."""
        logger.info("🛑 Shutting down...")

        # Shutdown all components
        for name, component in {**self.services, **self.gateways}.items():
            if hasattr(component, "shutdown") and callable(component.shutdown):
                try:
                    await component.shutdown()
                    logger.debug(f"Shutdown: {name}")
                except Exception as e:
                    logger.warning(f"Failed to shutdown {name}: {e}")

        logger.info("✅ Shutdown completed")
