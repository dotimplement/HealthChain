"""
FHIR Gateway for HealthChain.

This module provides a unified FHIR interface that acts as both a client for outbound
requests and a router for inbound API endpoints. It allows registration of custom
handlers for different FHIR operations using decorators, similar to services.
"""

import logging
from typing import Dict, List, Any, Callable, Type, Optional, TypeVar
from datetime import datetime

from fastapi import APIRouter, HTTPException, Body, Path, Depends
from fhir.resources.resource import Resource

# Try to import fhirclient, but make it optional
try:
    import fhirclient.client as fhir_client
except ImportError:
    fhir_client = None

from healthchain.gateway.core.base import BaseGateway
from healthchain.gateway.events.dispatcher import EHREvent, EHREventType

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


class FHIRGateway(BaseGateway, APIRouter):
    """
    Unified FHIR interface that combines client and router capabilities.

    FHIRGateway provides:
    1. Client functionality for making outbound requests to FHIR servers
    2. Router functionality for handling inbound FHIR API requests
    3. Decorator-based registration of custom handlers
    4. Support for FHIR resource transformations

    Example:
        ```python
        # Create a FHIR gateway
        from fhir.resources.patient import Patient
        from healthchain.gateway.clients import FHIRGateway

        fhir_gateway = FHIRGateway(base_url="https://r4.smarthealthit.org")

        # Register a custom read handler using decorator
        @fhir_gateway.read(Patient)
        def read_patient(patient: Patient) -> Patient:
            # Apply US Core profile transformation
            patient = fhir_gateway.profile_transform(patient, "us-core")
            return patient

        # Register gateway with HealthChainAPI
        app.register_gateway(fhir_gateway)
        ```
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        client: Optional[Any] = None,
        prefix: str = "/fhir",
        tags: List[str] = ["FHIR"],
        supported_resources: Optional[List[str]] = None,
        use_events: bool = True,
        **options,
    ):
        """
        Initialize a new FHIR gateway.

        Args:
            base_url: The base URL of the FHIR server for outbound requests
            client: An existing FHIR client instance to use, or None to create a new one
            prefix: URL prefix for inbound API routes
            tags: OpenAPI tags for documentation
            supported_resources: List of supported FHIR resource types (None for all)
            use_events: Whether to enable event dispatching functionality
            **options: Additional configuration options
        """
        # Initialize as BaseGateway
        BaseGateway.__init__(self, use_events=use_events, **options)

        # Initialize as APIRouter
        APIRouter.__init__(self, prefix=prefix, tags=tags)

        # Store event usage preference
        self.use_events = use_events

        # Create default FHIR client if not provided
        if client is None and base_url:
            if fhir_client is None:
                raise ImportError(
                    "fhirclient package is required. Install with 'pip install fhirclient'"
                )
            client = fhir_client.FHIRClient(
                settings={
                    "app_id": options.get("app_id", "healthchain"),
                    "api_base": base_url,
                }
            )

        self.client = client
        self.base_url = base_url

        # Router configuration
        self.supported_resources = supported_resources or [
            "Patient",
            "Practitioner",
            "Encounter",
            "Observation",
            "Condition",
            "MedicationRequest",
            "DocumentReference",
        ]

        # Handlers for resource operations
        self._resource_handlers: Dict[str, Dict[str, Callable]] = {}

        # Register default routes
        self._register_default_routes()

    def _register_default_routes(self):
        """Register default FHIR API routes."""

        # Metadata endpoint
        @self.get("/metadata")
        async def capability_statement():
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
                            for resource_type in self.supported_resources
                        ],
                    }
                ],
            }

        # Resource instance level operations are registered dynamically based on
        # the decorators used. See read(), update(), delete() methods.

        # Resource type level search operation
        @self.get("/{resource_type}")
        async def search_resources(
            resource_type: str = Path(..., description="FHIR resource type"),
            query_params: Dict = Depends(self._extract_query_params),
        ):
            """Search for FHIR resources."""
            self._validate_resource_type(resource_type)

            # Check if there's a custom search handler
            handler = self._get_resource_handler(resource_type, "search")
            if handler:
                return await handler(query_params)

            # Default search implementation
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "total": 0,
                "entry": [],
            }

        # Resource creation
        @self.post("/{resource_type}")
        async def create_resource(
            resource: Dict = Body(..., description="FHIR resource"),
            resource_type: str = Path(..., description="FHIR resource type"),
        ):
            """Create a new FHIR resource."""
            self._validate_resource_type(resource_type)

            # Check if there's a custom create handler
            handler = self._get_resource_handler(resource_type, "create")
            if handler:
                return await handler(resource)

            # Default create implementation
            return {
                "resourceType": resource_type,
                "id": "generated-id",
                "status": "created",
            }

    def _validate_resource_type(self, resource_type: str):
        """
        Validate that the requested resource type is supported.

        Args:
            resource_type: FHIR resource type to validate

        Raises:
            HTTPException: If resource type is not supported
        """
        if resource_type not in self.supported_resources:
            raise HTTPException(
                status_code=404,
                detail=f"Resource type {resource_type} is not supported",
            )

    async def _extract_query_params(self, request) -> Dict:
        """
        Extract query parameters from request.

        Args:
            request: FastAPI request object

        Returns:
            Dictionary of query parameters
        """
        return dict(request.query_params)

    def _get_resource_handler(
        self, resource_type: str, operation: str
    ) -> Optional[Callable]:
        """
        Get a registered handler for a resource type and operation.

        Args:
            resource_type: FHIR resource type
            operation: Operation name (read, search, create, update, delete)

        Returns:
            Handler function if registered, None otherwise
        """
        handlers = self._resource_handlers.get(resource_type, {})
        return handlers.get(operation)

    def _register_resource_handler(
        self, resource_type: str, operation: str, handler: Callable
    ):
        """
        Register a handler for a resource type and operation.

        Args:
            resource_type: FHIR resource type
            operation: Operation name (read, search, create, update, delete)
            handler: Handler function
        """
        if resource_type not in self._resource_handlers:
            self._resource_handlers[resource_type] = {}

        self._resource_handlers[resource_type][operation] = handler

        # Ensure the resource type is in supported_resources
        if resource_type not in self.supported_resources:
            self.supported_resources.append(resource_type)

    def read(self, resource_class: Type[T]):
        """
        Decorator to register a handler for reading a specific resource type.

        Args:
            resource_class: FHIR resource class (e.g., Patient, Observation)

        Returns:
            Decorator function that registers the handler
        """
        resource_type = resource_class.__name__

        def decorator(handler: Callable[[T], T]):
            self._register_resource_handler(resource_type, "read", handler)

            # Register the route
            @self.get(f"/{resource_type}/{{id}}")
            async def read_resource(id: str = Path(..., description="Resource ID")):
                """Read a specific FHIR resource instance."""
                try:
                    # Get the resource from the FHIR server
                    if self.client:
                        resource_data = self.client.server.request_json(
                            f"{resource_type}/{id}"
                        )
                        resource = resource_class(resource_data)
                    else:
                        # Mock resource for testing
                        resource = resource_class(
                            {"id": id, "resourceType": resource_type}
                        )

                    # Call the handler
                    result = handler(resource)

                    # Emit event if we have an event dispatcher
                    if hasattr(self, "event_dispatcher") and self.event_dispatcher:
                        self._emit_fhir_event("read", resource_type, id, result)

                    # Return as dict
                    return (
                        result.model_dump() if hasattr(result, "model_dump") else result
                    )

                except Exception as e:
                    logger.exception(f"Error reading {resource_type}/{id}: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error reading {resource_type}/{id}: {str(e)}",
                    )

            return handler

        return decorator

    def update(self, resource_class: Type[T]):
        """
        Decorator to register a handler for updating a specific resource type.

        Args:
            resource_class: FHIR resource class (e.g., Patient, Observation)

        Returns:
            Decorator function that registers the handler
        """
        resource_type = resource_class.__name__

        def decorator(handler: Callable[[T], T]):
            self._register_resource_handler(resource_type, "update", handler)

            # Register the route
            @self.put(f"/{resource_type}/{{id}}")
            async def update_resource(
                resource: Dict = Body(..., description="FHIR resource"),
                id: str = Path(..., description="Resource ID"),
            ):
                """Update a specific FHIR resource instance."""
                try:
                    # Convert to resource object
                    resource_obj = resource_class(resource)

                    # Call the handler
                    result = handler(resource_obj)

                    # Emit event if we have an event dispatcher
                    if hasattr(self, "event_dispatcher") and self.event_dispatcher:
                        self._emit_fhir_event("update", resource_type, id, result)

                    # Return as dict
                    return (
                        result.model_dump() if hasattr(result, "model_dump") else result
                    )

                except Exception as e:
                    logger.exception(f"Error updating {resource_type}/{id}: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error updating {resource_type}/{id}: {str(e)}",
                    )

            return handler

        return decorator

    def delete(self, resource_class: Type[T]):
        """
        Decorator to register a handler for deleting a specific resource type.

        Args:
            resource_class: FHIR resource class (e.g., Patient, Observation)

        Returns:
            Decorator function that registers the handler
        """
        resource_type = resource_class.__name__

        def decorator(handler: Callable[[str], Any]):
            self._register_resource_handler(resource_type, "delete", handler)

            # Register the route
            @self.delete(f"/{resource_type}/{{id}}")
            async def delete_resource(id: str = Path(..., description="Resource ID")):
                """Delete a specific FHIR resource instance."""
                try:
                    # Call the handler
                    result = handler(id)

                    # Emit event if we have an event dispatcher
                    if hasattr(self, "event_dispatcher") and self.event_dispatcher:
                        self._emit_fhir_event("delete", resource_type, id, None)

                    # Default response if handler doesn't return anything
                    if result is None:
                        return {
                            "resourceType": "OperationOutcome",
                            "issue": [
                                {
                                    "severity": "information",
                                    "code": "informational",
                                    "diagnostics": f"Successfully deleted {resource_type}/{id}",
                                }
                            ],
                        }

                    return result

                except Exception as e:
                    logger.exception(f"Error deleting {resource_type}/{id}: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error deleting {resource_type}/{id}: {str(e)}",
                    )

            return handler

        return decorator

    def search(self, resource_class: Type[T]):
        """
        Decorator to register a handler for searching a specific resource type.

        Args:
            resource_class: FHIR resource class (e.g., Patient, Observation)

        Returns:
            Decorator function that registers the handler
        """
        resource_type = resource_class.__name__

        def decorator(handler: Callable[[Dict], Any]):
            self._register_resource_handler(resource_type, "search", handler)
            return handler

        return decorator

    def create(self, resource_class: Type[T]):
        """
        Decorator to register a handler for creating a specific resource type.

        Args:
            resource_class: FHIR resource class (e.g., Patient, Observation)

        Returns:
            Decorator function that registers the handler
        """
        resource_type = resource_class.__name__

        def decorator(handler: Callable[[T], T]):
            self._register_resource_handler(resource_type, "create", handler)
            return handler

        return decorator

    def operation(self, operation_name: str):
        """
        Decorator to register a handler for a custom FHIR operation.

        Args:
            operation_name: The operation name to handle

        Returns:
            Decorator function that registers the handler
        """

        def decorator(handler):
            self.register_handler(operation_name, handler)
            return handler

        return decorator

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
