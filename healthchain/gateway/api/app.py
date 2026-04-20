"""
HealthChainAPI - FastAPI wrapper with healthcare integration capabilities.

This module provides the main HealthChainAPI class that wraps FastAPI and manages
healthcare-specific gateways, routes, middleware, and capabilities.
"""

import logging
import os
import re

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from typing import Dict, Optional, Type, Union

from healthchain.gateway.base import BaseGateway, BaseProtocolHandler
from healthchain.gateway.events.dispatcher import EventDispatcher
from healthchain.gateway.api.dependencies import get_app

logger = logging.getLogger(__name__)

# ── Half-block pixel font (4 wide × 3 tall, encodes 2 logical rows per char) ──
_HB = {
    "H": ["█  █", "█▀▀█", "▀  ▀"],
    "E": ["█▀▀▀", "█▀▀ ", "▀▀▀▀"],
    "A": ["▄▀▀▄", "█▀▀█", "▀  ▀"],
    "L": ["█   ", "█   ", "▀▀▀▀"],
    "T": ["▀██▀", " ██ ", " ▀▀ "],
    "C": ["▄▀▀▀", "█   ", " ▀▀▀"],
    "I": ["▀██▀", " ██ ", "▀▀▀▀"],
    "N": ["█▄ █", "█ ▀█", "▀  ▀"],
}


def _render_word(word: str) -> list[str]:
    rows = [""] * 3
    for j, ch in enumerate(word):
        for r in range(3):
            rows[r] += _HB[ch][r] + (" " if j < len(word) - 1 else "")
    return rows


def _gradient(text: str, t0: float, t1: float) -> str:
    r0, g0, b0 = 0, 215, 255
    r1, g1, b1 = 192, 132, 252
    visible = [(i, c) for i, c in enumerate(text) if c != " "]
    total = max(len(visible) - 1, 1)
    chars = list(text)
    for idx, (i, c) in enumerate(visible):
        t = t0 + (t1 - t0) * (idx / total)
        r = int(r0 + (r1 - r0) * t)
        g = int(g0 + (g1 - g0) * t)
        b = int(b0 + (b1 - b0) * t)
        chars[i] = f"\033[38;2;{r};{g};{b}m{c}\033[0m"
    return "".join(chars)


def _vlen(s: str) -> int:
    return len(re.sub(r"\033\[[^m]*m", "", s))


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _vlen(s))


def _val_bool(enabled: bool) -> str:
    return (
        "\033[38;2;0;255;135m✓ enabled\033[0m"
        if enabled
        else "\033[38;2;255;85;85m✗ disabled\033[0m"
    )


def _val_env(env: str) -> str:
    c = {"production": "\033[38;2;0;255;135m", "staging": "\033[38;2;0;215;255m"}.get(
        env, "\033[38;2;255;200;50m"
    )
    return f"{c}{env}\033[0m"


def _val_auth(auth: str) -> str:
    if auth == "none":
        return "\033[38;2;255;200;50mnone\033[0m"
    return f"\033[38;2;0;255;135m{auth}\033[0m"


def _val_eval(enabled: bool, provider: str) -> str:
    if enabled:
        return f"\033[38;2;0;255;135m✓ {provider}\033[0m"
    return "\033[2m✗ disabled\033[0m"


def _status_row(key: str, value: str) -> str:
    return f"\033[1m\033[38;2;0;255;135m{key}\033[0m  {value}"


def _print_startup_banner(
    title: str,
    version: str,
    gateways: dict,
    services: dict,
    docs_url: str,
    port: int = 8000,
    service_type: Optional[str] = None,
    config=None,
    config_path: Optional[str] = None,
) -> None:
    """Print pixel-wordmark banner with live status panel."""
    health_rows = _render_word("HEALTH")
    chain_rows = _render_word("CHAIN")
    health_w = len(health_rows[0])
    chain_w = len(chain_rows[0])
    center_pad = (health_w - chain_w) // 2
    LOGO_COL = 38

    # ── resolve status values from config or sensible defaults ──
    svc_type = (
        service_type
        or (config.service.type if config else None)
        or (
            list({**gateways, **services}.keys())[0]
            if {**gateways, **services}
            else "unknown"
        )
    )
    env = config.site.environment if config else "development"
    port = str(port)
    site = config.site.name if config else None
    auth = config.security.auth if config else "none"
    tls = config.security.tls.enabled if config else False
    hipaa = config.compliance.hipaa if config else False
    eval_enabled = config.eval.enabled if config else False
    eval_provider = config.eval.provider if config else "mlflow"
    # Check registered gateways first, then fall back to env var presence
    fhir_configured = any(
        hasattr(gw, "connection_manager")
        and gw.connection_manager
        and getattr(gw.connection_manager, "sources", None)
        for gw in gateways.values()
    ) or any(k.endswith("_CLIENT_ID") for k in os.environ)

    status: list[str] = [
        f"\033[1m\033[38;2;255;121;198m{title}\033[0m  \033[2mv{version}\033[0m",
        "",
        _status_row("type:       ", svc_type),
        _status_row("environment:", _val_env(env)),
        _status_row("port:       ", f"\033[1m{port}\033[0m"),
    ]
    if site:
        status.append(_status_row("site:       ", site))
    status += [
        "",
        _status_row("auth:       ", _val_auth(auth)),
        _status_row(
            "fhir creds: ",
            "\033[38;2;0;255;135m✓ configured\033[0m"
            if fhir_configured
            else "\033[38;2;255;200;50m✗ not set\033[0m",
        ),
        _status_row("tls:        ", _val_bool(tls)),
        _status_row("hipaa:      ", _val_bool(hipaa)),
        _status_row("eval:       ", _val_eval(eval_enabled, eval_provider)),
        "",
        _status_row("config:     ", f"\033[1m{config_path or '(none)'}\033[0m"),
        _status_row("docs:       ", f"\033[1mhttp://localhost:{port}{docs_url}\033[0m"),
    ]

    # ── build logo lines, vertically centred against status height ──
    n = 3
    inner: list[str] = []
    for i in range(n):
        inner.append(
            _pad(
                "  " + _gradient(health_rows[i], i / (n * 2), 0.5 + i / (n * 2)),
                LOGO_COL,
            )
        )
    inner.append(" " * LOGO_COL)
    for i in range(n):
        inner.append(
            _pad(
                "  "
                + " " * center_pad
                + _gradient(chain_rows[i], 0.1 + i / (n * 2), 0.6 + i / (n * 2)),
                LOGO_COL,
            )
        )

    top = (len(status) - len(inner)) // 2
    bot = len(status) - len(inner) - top
    logo_lines = [" " * LOGO_COL] * top + inner + [" " * LOGO_COL] * bot

    max_status_w = max(_vlen(s) for s in status)
    inner_w = LOGO_COL + 3 + max_status_w
    border = "\033[38;2;99;102;241m"  # indigo
    rst = "\033[0m"

    print()
    print(f"{border}╭{'─' * (inner_w + 2)}╮{rst}")
    for logo_line, s in zip(logo_lines, status):
        padding = " " * (max_status_w - _vlen(s))
        print(f"{border}│{rst} {logo_line}   {s}{padding} {border}│{rst}")
    print(f"{border}╰{'─' * (inner_w + 2)}╯{rst}")
    print()


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
        service_type: Optional[str] = None,
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

        # Display metadata for banner (when running outside healthchain serve)
        self._port: Optional[int] = None
        self._service_type = service_type

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
            from healthchain.config.appconfig import AppConfig

            _config = AppConfig.load()
            origins = _config.security.allowed_origins if _config else ["*"]
            self.add_middleware(
                CORSMiddleware,
                allow_origins=origins,
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
        from healthchain.config.appconfig import AppConfig

        config = AppConfig.load()
        port = self._port or (config.service.port if config else 8000)
        _print_startup_banner(
            title=config.name if config else self.title,
            version=config.version if config else self.version,
            gateways=self.gateways,
            services=self.services,
            docs_url=self.docs_url or "/docs",
            port=port,
            service_type=self._service_type,
            config=config,
            config_path="./healthchain.yaml" if config else None,
        )

        # Initialize components
        for name, component in {**self.gateways, **self.services}.items():
            if hasattr(component, "startup") and callable(component.startup):
                try:
                    await component.startup()
                    logger.debug(f"Initialized: {name}")
                except Exception as e:
                    logger.warning(f"Failed to initialize {name}: {e}")

    def run(self, host: str = "0.0.0.0", port: int = 8000, **kwargs) -> None:
        """Run the application with uvicorn.

        Convenience wrapper for local development and cookbooks. For production,
        use `healthchain serve` which reads healthchain.yaml for TLS, port, etc.

        Args:
            host: Host to bind to (default: 0.0.0.0)
            port: Port to bind to (default: 8000)
            **kwargs: Passed through to uvicorn.run (e.g. reload=True, workers=4)

        Example:
            app = HealthChainAPI(title="My App")
            app.run(port=8888)
            app.run(port=8888, reload=True)  # with hot reload
        """
        import uvicorn

        self._port = port
        uvicorn.run(self, host=host, port=port, **kwargs)

    async def _shutdown(self) -> None:
        """Handle graceful shutdown."""
        for name, component in {**self.services, **self.gateways}.items():
            if hasattr(component, "shutdown") and callable(component.shutdown):
                try:
                    await component.shutdown()
                    logger.debug(f"Shutdown: {name}")
                except Exception as e:
                    logger.warning(f"Failed to shutdown {name}: {e}")
