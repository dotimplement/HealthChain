"""
SOAP protocol implementation for HealthChain Gateway.

This module provides SOAP integration with healthcare systems, particularly
Epic's CDA document processing services.
"""

import logging

from typing import Any, Callable, Dict, Optional, TypeVar, Union

from pydantic import BaseModel

from healthchain.gateway.base import BaseProtocolHandler
from healthchain.gateway.events.dispatcher import EventDispatcher
from healthchain.gateway.soap.events import create_notereader_event
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.gateway.soap.fastapi_server import create_fastapi_soap_router

logger = logging.getLogger(__name__)


# Type variable for self-referencing return types
T = TypeVar("T", bound="NoteReaderService")


class NoteReaderConfig(BaseModel):
    """Configuration options for NoteReader service"""

    service_name: str = "ICDSServices"
    namespace: str = "urn:epic-com:Common.2013.Services"
    system_type: str = "EHR_CDA"
    default_mount_path: str = "/notereader"


class NoteReaderService(BaseProtocolHandler[CdaRequest, CdaResponse]):
    """
    Service for Epic NoteReader SOAP protocol integration.

    Provides SOAP integration with healthcare systems, particularly
    Epic's NoteReader CDA document processing and other SOAP-based
    healthcare services.

    Example:
        ```python
        # Create NoteReader service with default configuration
        service = NoteReaderService()

        # Register method handler with decorator
        @service.method("ProcessDocument")
        def process_document(request: CdaRequest) -> CdaResponse:
            # Process the document
            return CdaResponse(
                document="Processed document content",
                error=None
            )

        # Register the service with the API
        app.register_service(service)
        ```
    """

    def __init__(
        self,
        config: Optional[NoteReaderConfig] = None,
        event_dispatcher: Optional[EventDispatcher] = None,
        use_events: bool = True,
        **options,
    ):
        """
        Initialize a new NoteReader service.

        Args:
            config: Configuration options for the service
            event_dispatcher: Optional event dispatcher for publishing events
            use_events: Whether to enable event dispatching functionality
            **options: Additional options for the service
        """
        # Initialize the base protocol handler
        super().__init__(use_events=use_events, **options)

        # Initialize specific configuration
        self.config = config or NoteReaderConfig()
        self._handler_metadata = {}

        # Set event dispatcher if provided
        if event_dispatcher and use_events:
            self.events.set_dispatcher(event_dispatcher)

    def method(self, method_name: str) -> Callable:
        """
        Decorator to register a handler for a specific SOAP method.

        Args:
            method_name: The SOAP method name to handle (e.g. ProcessDocument)

        Returns:
            Decorator function that registers the handler
        """

        def decorator(handler):
            self.register_handler(method_name, handler)
            return handler

        return decorator

    def handle(self, operation: str, **params) -> Union[CdaResponse, Dict]:
        """
        Process a SOAP request using registered handlers.

        Args:
            operation: The SOAP method name e.g. ProcessDocument
            **params: Either a CdaRequest object or raw parameters

        Returns:
            CdaResponse or dict containing the response
        """
        # Check if we have a handler for this operation
        if operation not in self._handlers:
            logger.warning(f"No handler registered for operation: {operation}")
            return CdaResponse(document="", error=f"No handler for {operation}")

        # Extract or build the request object
        request = self._extract_request(operation, params)
        if not request:
            return CdaResponse(document="", error="Invalid request parameters")

        # Execute the handler with the request
        return self._execute_handler(operation, request)

    def _extract_request(self, operation: str, params: Dict) -> Optional[CdaRequest]:
        """
        Extract or construct a CdaRequest from parameters.

        Args:
            operation: The SOAP method name e.g. ProcessDocument
            params: The parameters passed to handle

        Returns:
            CdaRequest object or None if request couldn't be constructed
        """
        try:
            # Case 1: Direct CdaRequest passed as a parameter
            if "request" in params and isinstance(params["request"], CdaRequest):
                return params["request"]

            # Case 2: Direct CdaRequest passed as a single parameter
            if len(params) == 1:
                param_values = list(params.values())
                if isinstance(param_values[0], CdaRequest):
                    return param_values[0]

            # Case 3: Build CdaRequest from params
            if operation in self._handlers:
                return CdaRequest(**params)

            logger.warning(f"Unable to construct CdaRequest for operation: {operation}")
            return None

        except Exception as e:
            logger.error(f"Error constructing CdaRequest: {str(e)}", exc_info=True)
            return None

    def _execute_handler(self, operation: str, request: CdaRequest) -> CdaResponse:
        """
        Execute a registered handler with the given request.

        Args:
            operation: The SOAP method name e.g. ProcessDocument
            request: CdaRequest object containing parameters

        Returns:
            CdaResponse object
        """
        handler = self._handlers[operation]

        try:
            # Call the handler directly with the CdaRequest
            result = handler(request)

            # Process the result
            return self._process_result(result)

        except Exception as e:
            logger.error(f"Error in {operation} handler: {str(e)}", exc_info=True)
            return CdaResponse(document="", error=str(e))

    def _process_result(self, result: Any) -> CdaResponse:
        """
        Convert handler result to a CdaResponse.

        Args:
            result: The result returned by the handler

        Returns:
            CdaResponse object
        """
        # If the result is already a CdaResponse, return it
        if isinstance(result, CdaResponse):
            return result
        try:
            # Try to convert to CdaResponse if possible
            if isinstance(result, dict):
                return CdaResponse(**result)
            logger.warning(f"Unexpected result type from handler: {type(result)}")
            return CdaResponse(document=str(result), error=None)
        except Exception as e:
            logger.error(f"Error processing result to CdaResponse: {str(e)}")
            return CdaResponse(document="", error="Invalid response format")

    def create_fastapi_router(self):
        if "ProcessDocument" not in self._handlers:
            raise ValueError("No ProcessDocument handler registered")

        handler = self._handlers["ProcessDocument"]

        return create_fastapi_soap_router(
            service_name=self.config.service_name,
            namespace=self.config.namespace,
            handler=handler,
        )

    def _emit_document_event(
        self, operation: str, request: CdaRequest, response: CdaResponse
    ):
        """
        Emit an event for document processing.

        Args:
            operation: The SOAP method name e.g. ProcessDocument
            request: The CdaRequest object
            response: The CdaResponse object
        """
        self.events.emit_event(
            create_notereader_event,
            operation,
            request,
            response,
            use_events=self.use_events,
            system_type=self.config.system_type,
        )

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata for this service.

        Returns:
            Dictionary of service metadata
        """
        return {
            "service_type": self.__class__.__name__,
            "operations": self.get_capabilities(),
            "system_type": self.config.system_type,
            "soap_service": self.config.service_name,
            "namespace": self.config.namespace,
            "mount_path": self.config.default_mount_path,
        }
