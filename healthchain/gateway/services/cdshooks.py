"""
CDS Hooks protocol integration for HealthChain Gateway.

This module implements the CDS Hooks standard for clinical decision support
integration with EHR systems.
"""

from typing import Dict, List, Optional, Any, Callable, Union, TypeVar
import logging
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel

from healthchain.gateway.core.base import InboundAdapter, BaseService
from healthchain.gateway.events.dispatcher import EventDispatcher

from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsdiscovery import CDSService, CDSServiceInformation
from healthchain.models.responses.cdsresponse import CDSResponse
from healthchain.sandbox.workflows import UseCaseMapping

logger = logging.getLogger(__name__)


# Type variable for self-referencing return types
T = TypeVar("T", bound="CDSHooksAdapter")


# TODO: Abstract configs to a base class
class CDSHooksConfig(BaseModel):
    """Configuration options for CDS Hooks services"""

    system_type: str = "CDS-HOOKS"
    base_path: str = "/cds"
    discovery_path: str = "/cds-discovery"
    service_path: str = "/cds-services"
    allowed_hooks: List[str] = UseCaseMapping.ClinicalDecisionSupport.allowed_workflows


class CDSHooksAdapter(InboundAdapter):
    """
    Adapter for CDS Hooks protocol integration.

    The adapter manages the lifecycle of CDS hook requests, from receiving the initial
    request to executing the appropriate handler and formatting the response. It supports
    both synchronous and asynchronous handler functions.
    """

    def __init__(self, config: Optional[CDSHooksConfig] = None, **options):
        """
        Initialize a new CDS Hooks adapter.

        Args:
            config: Configuration options for the adapter
            **options: Additional options passed to the parent class
        """
        super().__init__(**options)
        self.config = config or CDSHooksConfig()
        self._handler_metadata = {}

    def register_handler(
        self,
        operation: str,
        handler: Callable,
        id: str,
        title: Optional[str] = None,
        description: Optional[str] = "CDS Hook service created by HealthChain",
        usage_requirements: Optional[str] = None,
    ) -> T:
        """
        Register a handler for a specific CDS hook operation with metadata. e.g. patient-view

        Extends the base register_handler method to add CDS Hooks specific metadata.

        Args:
            operation: The hook type (e.g., "patient-view")
            handler: Function that will handle the operation
            id: Unique identifier for this specific hook
            title: Human-readable title for this hook. If not provided, the operation name will be used.
            description: Human-readable description of this hook.
            usage_requirements: Human-readable description of any preconditions for the use of this CDS service.

        Returns:
            Self, to allow for method chaining
        """
        # Use the parent class's register_handler method
        super().register_handler(operation, handler)

        # Add CDS-specific metadata
        self._handler_metadata[operation] = {
            "id": id,
            "title": title or operation.replace("-", " ").title(),
            "description": description,
            "usage_requirements": usage_requirements,
        }

        return self

    async def handle(self, operation: str, **params) -> Union[CDSResponse, Dict]:
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
        return await self._execute_handler(request)

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

    async def _execute_handler(self, request: CDSRequest) -> CDSResponse:
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

            # Support both async and non-async handlers
            if asyncio.iscoroutinefunction(handler):
                result = await handler(request)
            else:
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

    @classmethod
    def create(cls, **options) -> T:
        """
        Factory method to create a new adapter with default configuration.

        Args:
            **options: Options to pass to the constructor

        Returns:
            New CDSHooksAdapter instance
        """
        return cls(config=CDSHooksConfig(), **options)


class CDSHooksService(BaseService):
    """
    CDS Hooks service implementation with FastAPI integration.

    CDS Hooks is an HL7 standard that allows EHR systems to request
    clinical decision support from external services at specific points
    in the clinical workflow.

    Example:
        ```python
        # Create CDS Hooks service with default adapter
        cds_service = CDSHooksService()

        # Mount to a FastAPI app
        app = FastAPI()
        cds_service.add_to_app(app)

        # Register a hook handler with decorator
        @cds_service.hook("patient-view", id="patient-summary")
        async def handle_patient_view(request: CDSRequest) -> CDSResponse:
            # Generate cards based on patient context
            return CDSResponse(cards=[
                {
                    "summary": "Example guidance",
                    "indicator": "info",
                    "source": {
                        "label": "HealthChain Gateway"
                    }
                }
            ])
        ```
    """

    def __init__(
        self,
        adapter: Optional[CDSHooksAdapter] = None,
        event_dispatcher: Optional[EventDispatcher] = None,
    ):
        """
        Initialize a new CDS Hooks service.

        Args:
            adapter: CDSHooksAdapter instance for handling hook requests (creates default if None)
            event_dispatcher: Optional EventDispatcher instance
        """
        super().__init__(
            adapter=adapter or CDSHooksAdapter.create(),
            event_dispatcher=event_dispatcher or EventDispatcher(),
        )

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

        This is a convenience method that delegates to the adapter's register_handler method.

        Args:
            hook_type: The CDS Hook type (e.g., "patient-view", "medication-prescribe")
            id: Unique identifier for this specific hook
            title: Human-readable title for this hook. If not provided, the hook type will be used.
            description: Human-readable description of this hook
            usage_requirements: Human-readable description of any preconditions for the use of this CDS service.

        Returns:
            Decorator function that registers the handler
        """

        def decorator(handler):
            if hook_type not in self.adapter.config.allowed_hooks:
                raise ValueError(
                    f"Hook type {hook_type} is not allowed. Must be one of: {self.adapter.config.allowed_hooks}"
                )

            self.adapter.register_handler(
                operation=hook_type,
                handler=handler,
                id=id,
                title=title,
                description=description,
                usage_requirements=usage_requirements,
            )
            return handler

        return decorator

    async def handle_discovery(self) -> CDSServiceInformation:
        """
        Get the CDS Hooks service definition for discovery.

        Returns:
            CDSServiceInformation containing the CDS Hooks service definition
        """
        services = []
        hook_metadata = self.adapter.get_metadata()

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

    async def handle_request(self, request: CDSRequest) -> CDSResponse:
        """
        CDS service endpoint handler.

        Args:
            request: CDSRequest object

        Returns:
            CDSResponse object
        """
        return await self.adapter.handle(request.hook, request=request)

    # TODO: Should be delegated to the HealthChainAPI wrapper
    def add_to_app(self, app: FastAPI, path: Optional[str] = None) -> None:
        """
        Add this service to a FastAPI application.

        Args:
            app: The FastAPI application to add to
            path: Path to add the service at (uses adapter config if None)
        """
        base_path = path or self.adapter.config.base_path
        if base_path:
            base_path = base_path.rstrip("/")

        # Register the discovery endpoint
        discovery_path = self.adapter.config.discovery_path.lstrip("/")
        discovery_endpoint = (
            f"{base_path}/{discovery_path}" if base_path else discovery_path
        )
        app.add_api_route(
            discovery_endpoint,
            self.handle_discovery,
            methods=["GET"],
            response_model_exclude_none=True,
        )
        logger.info(f"CDS Hooks discovery endpoint added at {discovery_endpoint}")

        # Register service endpoints for each hook
        service_path = self.adapter.config.service_path.lstrip("/")
        for metadata in self.adapter.get_metadata():
            hook_id = metadata["id"]
            if hook_id:
                service_endpoint = (
                    f"{base_path}/{service_path}/{hook_id}"
                    if base_path
                    else f"{service_path}/{hook_id}"
                )
                app.add_api_route(
                    service_endpoint,
                    self.handle_request,
                    methods=["POST"],
                    response_model_exclude_none=True,
                )
                logger.info(f"CDS Hooks service endpoint added at {service_endpoint}")
