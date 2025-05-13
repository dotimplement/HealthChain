"""
HealthChainAPI - FastAPI wrapper with healthcare integration capabilities.

This module provides the main HealthChainAPI class that wraps FastAPI and manages
healthcare-specific services, routes, middleware, and capabilities.
"""

import logging
import importlib
import inspect

from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from typing import Dict, Optional, Type, Union, Set

from healthchain.gateway.core.base import BaseService
# from healthchain.config import get_config

logger = logging.getLogger(__name__)


class HealthChainAPI(FastAPI):
    """
    HealthChainAPI wraps FastAPI to provide healthcare-specific integrations.

    This class extends FastAPI to provide additional capabilities for:
    - Managing healthcare services (FHIR, CDA, CDS Hooks, SOAP, etc.)
    - Routing and transforming healthcare data
    - Handling healthcare-specific authentication and authorization
    - Managing healthcare-specific configurations
    - Providing capability statements and service discovery

    Example:
        ```python
        app = HealthChainAPI()

        # Register services
        app.register_service(NoteReaderService)
        app.register_service(CDSHooksService)

        # Register routers
        app.register_router(FhirRouter)

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
        **kwargs,
    ):
        """
        Initialize the HealthChainAPI application.

        Args:
            title: API title for documentation
            description: API description for documentation
            version: API version
            enable_cors: Whether to enable CORS middleware
            **kwargs: Additional keyword arguments to pass to FastAPI
        """
        super().__init__(
            title=title, description=description, version=version, **kwargs
        )

        self.services: Dict[str, BaseService] = {}
        self.service_endpoints: Dict[str, Set[str]] = {}
        # self.config = get_config()

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

    def register_service(
        self, service_class: Type[BaseService], path: Optional[str] = None, **options
    ) -> None:
        """
        Register a service with the API and mount its endpoints.

        Args:
            service_class: The service class to register
            path: Optional override for the service's mount path
            **options: Options to pass to the service constructor
        """
        try:
            # Check if instance is already provided
            if isinstance(service_class, BaseService):
                service = service_class
                service_name = service.__class__.__name__
            else:
                # Create a new instance
                service = service_class(**options)
                service_name = service_class.__name__

            # Add to internal service registry
            self.services[service_name] = service

            # Add service routes to FastAPI app
            self._add_service_routes(service, path)

        except Exception as e:
            logger.error(
                f"Failed to register service {service_class.__name__}: {str(e)}"
            )
            raise

    def _add_service_routes(
        self, service: BaseService, path: Optional[str] = None
    ) -> None:
        """
        Add service routes to the FastAPI app.

        This method replaces the add_to_app method in service classes by handling the
        registration of routes centrally in the HealthChainAPI class.

        Args:
            service: The service to add routes for
            path: Optional override for the service's mount path
        """
        service_name = service.__class__.__name__
        self.service_endpoints[service_name] = set()

        # Case 1: Services with get_routes implementation
        routes = service.get_routes(path)
        if routes:
            for route_path, methods, handler, kwargs in routes:
                for method in methods:
                    self.add_api_route(
                        path=route_path, endpoint=handler, methods=[method], **kwargs
                    )
                    self.service_endpoints[service_name].add(f"{method}:{route_path}")
                    logger.info(
                        f"Registered {method} route {route_path} for {service_name}"
                    )

        # Case 2: WSGI services (like SOAP)
        if hasattr(service, "create_wsgi_app") and callable(service.create_wsgi_app):
            # For SOAP/WSGI services
            wsgi_app = service.create_wsgi_app()

            # Determine mount path
            mount_path = path
            if (
                mount_path is None
                and hasattr(service, "adapter")
                and hasattr(service.adapter, "config")
            ):
                # Try to get the default path from the service adapter config
                mount_path = getattr(service.adapter.config, "default_mount_path", None)
                if not mount_path:
                    mount_path = getattr(service.adapter.config, "base_path", None)

            if not mount_path:
                # Fallback path based on service name
                mount_path = f"/{service_name.lower().replace('service', '')}"

            # Mount the WSGI app
            self.mount(mount_path, WSGIMiddleware(wsgi_app))
            self.service_endpoints[service_name].add(f"WSGI:{mount_path}")
            logger.info(f"Registered WSGI service {service_name} at {mount_path}")

        elif not routes:
            logger.warning(f"Service {service_name} does not provide any routes")

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

    def register_gateway(self, gateway) -> None:
        """
        Register a gateway with the API.

        This is a convenience method for registering gateways such as FHIRGateway.
        It registers the gateway as both a router and a service when applicable.

        Args:
            gateway: The gateway to register
        """
        # Register as a router if it inherits from APIRouter
        if isinstance(gateway, APIRouter):
            self.register_router(gateway)

        # Register as a service if it has service capabilities
        if hasattr(gateway, "get_routes") and callable(gateway.get_routes):
            self.register_service(gateway)

        # Store gateway in a collection for future reference if needed
        if not hasattr(self, "_gateways"):
            self._gateways = {}

        gateway_name = gateway.__class__.__name__
        self._gateways[gateway_name] = gateway

        logger.info(f"Registered gateway {gateway_name}")

    def _add_default_routes(self) -> None:
        """Add default routes for the API."""

        @self.get("/")
        async def root():
            """Root endpoint providing basic API information."""
            return {
                "name": self.title,
                "version": self.version,
                "description": self.description,
                "services": list(self.services.keys()),
            }

        @self.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy"}

        @self.get("/metadata")
        async def metadata():
            """Provide capability statement for the API."""
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
            # TODO: Change date to current date
            return {
                "resourceType": "CapabilityStatement",
                "status": "active",
                "date": "2023-10-01",
                "kind": "instance",
                "software": {
                    "name": self.title,
                    "version": self.version,
                },
                "implementation": {
                    "description": self.description,
                    "url": "/",
                },
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


def create_app(config: Optional[Dict] = None) -> HealthChainAPI:
    """
    Create HealthChainAPI application with default configuration.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured HealthChainAPI instance
    """
    app = HealthChainAPI()

    # Additional setup could be done here based on config

    return app
