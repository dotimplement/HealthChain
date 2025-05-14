"""
CDS Hooks protocol integration for HealthChain Gateway.

This module implements the CDS Hooks standard for clinical decision support
integration with EHR systems.
"""

import logging
from datetime import datetime

from typing import Dict, List, Optional, Any, Callable, Union, TypeVar
from pydantic import BaseModel

from healthchain.gateway.core.base import BaseGateway
from healthchain.gateway.events.dispatcher import (
    EventDispatcher,
    EHREvent,
    EHREventType,
)

from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsdiscovery import CDSService, CDSServiceInformation
from healthchain.models.responses.cdsresponse import CDSResponse
from healthchain.sandbox.workflows import UseCaseMapping

logger = logging.getLogger(__name__)


# Type variable for self-referencing return types
T = TypeVar("T", bound="CDSHooksGateway")


HOOK_TO_EVENT = {
    "patient-view": EHREventType.CDS_PATIENT_VIEW,
    "encounter-discharge": EHREventType.CDS_ENCOUNTER_DISCHARGE,
    "order-sign": EHREventType.CDS_ORDER_SIGN,
    "order-select": EHREventType.CDS_ORDER_SELECT,
}


# Configuration options for CDS Hooks gateway
class CDSHooksConfig(BaseModel):
    """Configuration options for CDS Hooks gateway"""

    system_type: str = "CDS-HOOKS"
    base_path: str = "/cds"
    discovery_path: str = "/cds-discovery"
    service_path: str = "/cds-services"
    allowed_hooks: List[str] = UseCaseMapping.ClinicalDecisionSupport.allowed_workflows


class CDSHooksGateway(BaseGateway[CDSRequest, CDSResponse]):
    """
    Gateway for CDS Hooks protocol integration.

    This gateway implements the CDS Hooks standard for integrating clinical decision
    support with EHR systems. It provides discovery and hook execution endpoints
    that conform to the CDS Hooks specification.

    Example:
        ```python
        # Create a CDS Hooks gateway
        cds_gateway = CDSHooksGateway()

        # Register a hook handler
        @cds_gateway.hook("patient-view", id="patient-summary")
        def handle_patient_view(request: CDSRequest) -> CDSResponse:
            # Create cards based on the patient context
            return CDSResponse(
                cards=[
                    {
                        "summary": "Patient has allergies",
                        "indicator": "warning",
                        "detail": "Patient has multiple allergies that may be relevant"
                    }
                ]
            )

        # Register the gateway with the API
        app.register_gateway(cds_gateway)
        ```
    """

    def __init__(
        self,
        config: Optional[CDSHooksConfig] = None,
        event_dispatcher: Optional[EventDispatcher] = None,
        use_events: bool = True,
        **options,
    ):
        """
        Initialize a new CDS Hooks gateway.

        Args:
            config: Configuration options for the gateway
            event_dispatcher: Optional event dispatcher for publishing events
            use_events: Whether to enable event dispatching functionality
            **options: Additional options for the gateway
        """
        # Initialize the base gateway
        super().__init__(use_events=use_events, **options)

        # Initialize specific configuration
        self.config = config or CDSHooksConfig()
        self._handler_metadata = {}

        # Set event dispatcher if provided
        if event_dispatcher and use_events:
            self.set_event_dispatcher(event_dispatcher)

    def hook(
        self,
        hook_type: str,
        id: str,
        title: Optional[str] = None,
        description: Optional[str] = "CDS Hook service created by HealthChain",
        usage_requirements: Optional[str] = None,
    ) -> Callable:
        """
        Decorator to register a handler for a specific CDS hook type.

        Args:
            hook_type: The CDS Hook type (e.g., "patient-view")
            id: Unique identifier for this specific hook
            title: Human-readable title for this hook. If not provided, the hook type will be used.
            description: Human-readable description of this hook
            usage_requirements: Human-readable description of any preconditions for the use of this CDS service.

        Returns:
            Decorator function that registers the handler
        """

        def decorator(handler):
            if hook_type not in self.config.allowed_hooks:
                raise ValueError(
                    f"Hook type {hook_type} is not allowed. Must be one of: {self.config.allowed_hooks}"
                )

            # Register the handler
            self.register_handler(hook_type, handler)

            # Add CDS-specific metadata
            self._handler_metadata[hook_type] = {
                "id": id,
                "title": title or hook_type.replace("-", " ").title(),
                "description": description,
                "usage_requirements": usage_requirements,
            }

            return handler

        return decorator

    def handle_discovery(self) -> CDSServiceInformation:
        """
        Get the CDS Hooks service definition for discovery.

        Returns:
            CDSServiceInformation containing the CDS Hooks service definition
        """
        services = []
        hook_metadata = self.get_metadata()

        for metadata in hook_metadata:
            service_info = CDSService(
                hook=metadata["hook"],
                description=metadata["description"],
                id=metadata["id"],
                title=metadata["title"],
                usage_requirements=metadata["usage_requirements"],
            )
            services.append(service_info)

        return CDSServiceInformation(services=services)

    def handle_request(self, request: CDSRequest) -> CDSResponse:
        """
        CDS service endpoint handler.

        Args:
            request: CDSRequest object

        Returns:
            CDSResponse object
        """
        # Get the hook type from the request
        hook_type = request.hook

        # Process the request using the appropriate handler
        response = self.handle(hook_type, request=request)

        # If we have an event dispatcher, emit an event for the hook execution
        if self.event_dispatcher and self.use_events:
            try:
                self._emit_hook_event(hook_type, request, response)
            except Exception as e:
                # Log error but don't fail the request
                logger.error(
                    f"Error dispatching event for CDS hook: {str(e)}", exc_info=True
                )

        return response

    def _extract_request(self, operation: str, params: Dict) -> Optional[CDSRequest]:
        """
        Extract or construct a CDSRequest from parameters.

        Args:
            operation: The hook type e.g. "patient-view"
            params: The parameters passed to handle

        Returns:
            CDSRequest object or None if request couldn't be constructed
        """
        try:
            # Case 1: Direct CDSRequest passed as a parameter
            if "request" in params and isinstance(params["request"], CDSRequest):
                return params["request"]

            # Case 2: First parameter is a CDSRequest
            if len(params) == 1 and isinstance(next(iter(params.values())), CDSRequest):
                return next(iter(params.values()))

            # Case 3: Operation matches a hook type - build a CDSRequest
            if operation in self._handlers:
                # Build a CDSRequest from operation and params
                return CDSRequest(**params)

            # No valid request could be constructed
            logger.warning(f"Unable to construct CDSRequest for hook type: {operation}")
            return None

        except Exception as e:
            logger.warning(f"Error constructing CDSRequest: {str(e)}", exc_info=True)
            return None

    def handle(self, operation: str, **params) -> Union[CDSResponse, Dict]:
        """
        Process a CDS Hooks request using registered handlers.

        Args:
            operation: The hook type being triggered e.g. "patient-view"
            **params: Either a CDSRequest object or raw parameters

        Returns:
            CDSResponse object with the results of the operation
        """
        if operation not in self._handlers:
            logger.warning(f"No handler registered for hook type: {operation}")
            return CDSResponse(cards=[])

        # Handle direct CDSRequest objects
        request = self._extract_request(operation, params)
        if not request:
            return CDSResponse(cards=[])

        # Execute the handler with the request
        return self._execute_handler(request)

    def _execute_handler(self, request: CDSRequest) -> CDSResponse:
        """
        Execute a registered CDS hook with the given request.

        Args:
            request: CDSRequest object containing hook parameters

        Returns:
            CDSResponse object with cards
        """
        hook_type = request.hook

        try:
            # Call the registered handler with the request model directly
            logger.debug(f"Calling handler for hook type: {hook_type}")
            handler = self._handlers[hook_type]

            result = handler(request)

            # Process the result
            return self._process_result(result)

        except Exception as e:
            logger.error(f"Error in CDS hook handler: {str(e)}", exc_info=True)
            return CDSResponse(cards=[])

    def _process_result(self, result: Any) -> CDSResponse:
        """
        Convert handler result to a CDSResponse.

        Args:
            result: The result returned by the handler

        Returns:
            CDSResponse object
        """
        # If the result is already a CDSResponse, return it
        if isinstance(result, CDSResponse):
            return result

        try:
            # Otherwise, create a CDSResponse from the result
            if isinstance(result, dict) and "cards" in result:
                return CDSResponse(**result)
            logger.warning(f"Unexpected result type from handler: {type(result)}")
            return CDSResponse(cards=[])
        except Exception as e:
            logger.error(f"Error processing result to CDSResponse: {str(e)}")
            return CDSResponse(cards=[])

    def _emit_hook_event(
        self, hook_type: str, request: CDSRequest, response: CDSResponse
    ):
        """
        Emit an event for CDS hook invocation.

        Args:
            hook_type: The hook type being invoked (e.g., "patient-view")
            request: The CDSRequest object
            response: The CDSResponse object
        """
        # Skip if events are disabled or no dispatcher
        if not self.event_dispatcher or not self.use_events:
            return

        # Use custom event creator if provided
        if self._event_creator:
            event = self._event_creator(hook_type, request, response)
            if event:
                self._run_async_publish(event)
            return

        # Get the event type from the mapping
        event_type = HOOK_TO_EVENT.get(hook_type, EHREventType.EHR_GENERIC)

        # Create a standard event
        event = EHREvent(
            event_type=event_type,
            source_system="CDS-Hooks",
            timestamp=datetime.now(),
            payload={
                "hook": hook_type,
                "hook_instance": request.hookInstance,
                "context": dict(request.context),
            },
            metadata={
                "cards_count": len(response.cards) if response.cards else 0,
            },
        )

        # Publish the event
        self._run_async_publish(event)

    def get_metadata(self) -> List[Dict[str, Any]]:
        """
        Get metadata for all registered hooks.

        Returns:
            List of hook metadata dictionaries
        """
        metadata = []

        for hook_type in self._handlers.keys():
            hook_metadata = self._handler_metadata.get(hook_type, {})
            metadata.append(
                {
                    "hook": hook_type,
                    "id": hook_metadata.get("id"),
                    "title": hook_metadata.get("title"),
                    "description": hook_metadata.get("description"),
                    "usage_requirements": hook_metadata.get("usage_requirements"),
                }
            )

        return metadata

    def get_routes(self, path: Optional[str] = None) -> List[tuple]:
        """
        Get routes for the CDS Hooks gateway.

        Args:
            path: Optional path to add the gateway at (uses config if None)

        Returns:
            List of route tuples (path, methods, handler, kwargs)
        """
        routes = []

        base_path = path or self.config.base_path
        if base_path:
            base_path = base_path.rstrip("/")

        # Register the discovery endpoint
        discovery_path = self.config.discovery_path.lstrip("/")
        discovery_endpoint = (
            f"{base_path}/{discovery_path}" if base_path else f"/{discovery_path}"
        )
        routes.append(
            (
                discovery_endpoint,
                ["GET"],
                self.handle_discovery,
                {"response_model_exclude_none": True},
            )
        )

        # Register service endpoints for each hook
        service_path = self.config.service_path.lstrip("/")
        for metadata in self.get_metadata():
            hook_id = metadata.get("id")
            if hook_id:
                service_endpoint = (
                    f"{base_path}/{service_path}/{hook_id}"
                    if base_path
                    else f"/{service_path}/{hook_id}"
                )
                routes.append(
                    (
                        service_endpoint,
                        ["POST"],
                        self.handle_request,
                        {"response_model_exclude_none": True},
                    )
                )

        return routes

    @classmethod
    def create(cls, **options) -> T:
        """
        Factory method to create a new CDS Hooks gateway with default configuration.

        Args:
            **options: Options to pass to the constructor

        Returns:
            New CDSHooksGateway instance
        """
        return cls(**options)
