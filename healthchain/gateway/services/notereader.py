"""
SOAP protocol implementation for HealthChain Gateway.

This module provides SOAP integration with healthcare systems, particularly
Epic's CDA document processing services.
"""

import logging
from typing import Optional, Dict, Any, Callable, TypeVar, Union

from spyne import Application
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from pydantic import BaseModel

from healthchain.gateway.core.base import InboundAdapter, BaseService
from healthchain.gateway.events.dispatcher import EventDispatcher
from healthchain.service.soap.epiccdsservice import CDSServices
from healthchain.models.requests import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.service.soap.model.epicclientfault import ClientFault
from healthchain.service.soap.model.epicserverfault import ServerFault

logger = logging.getLogger(__name__)


# Type variable for self-referencing return types
T = TypeVar("T", bound="NoteReaderAdapter")


class NoteReaderConfig(BaseModel):
    """Configuration options for NoteReader services"""

    service_name: str = "ICDSServices"
    namespace: str = "urn:epic-com:Common.2013.Services"
    system_type: str = "EHR_CDA"
    default_mount_path: str = "/notereader"


class NoteReaderAdapter(InboundAdapter):
    """
    Adapter implementation for clinical document processing via SOAP protocol.

    This adapter handles integration with healthcare systems that use SOAP-based
    protocols for clinical document exchange, particularly for processing CDA
    (Clinical Document Architecture) documents using Epic's NoteReader NLP service.
    It provides a standardized interface for registering handlers that process
    clinical documents and return structured responses.
    """

    def __init__(self, config: Optional[NoteReaderConfig] = None, **options):
        """
        Initialize a new NoteReader adapter.

        Args:
            config: Configuration options for the adapter
            **options: Additional options passed to the parent class
        """
        super().__init__(**options)
        self.config = config or NoteReaderConfig()
        self._handler_metadata = {}

    def register_handler(self, operation: str, handler: Callable, **metadata) -> T:
        """
        Register a handler for a specific SOAP method. e.g. ProcessDocument

        Extends the base register_handler method to add additional metadata
        specific to SOAP services.

        Args:
            operation: The SOAP method name to handle e.g. ProcessDocument
            handler: Function that will handle the operation
            **metadata: Additional metadata for the handler

        Returns:
            Self, to allow for method chaining
        """
        # Use parent class's register_handler
        super().register_handler(operation, handler)

        # Store any additional metadata
        if metadata:
            self._handler_metadata[operation] = metadata

        return self

    async def handle(self, operation: str, **params) -> Union[CdaResponse, Dict]:
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
        return await self._execute_handler(operation, request)

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

    async def _execute_handler(
        self, operation: str, request: CdaRequest
    ) -> CdaResponse:
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

    @classmethod
    def create(cls, **options) -> T:
        """
        Factory method to create a new adapter with default configuration.

        Args:
            **options: Options to pass to the constructor

        Returns:
            New NoteReaderAdapter instance
        """
        return cls(config=NoteReaderConfig(), **options)


class NoteReaderService(BaseService):
    """
    Epic NoteReader SOAP service implementation with FastAPI integration.

    Provides SOAP integration with healthcare systems, particularly
    Epic's NoteReader CDA document processing and other SOAP-based
    healthcare services.

    Example:
        ```python
        # Create NoteReader service with default adapter
        service = NoteReaderService()

        # Add to a FastAPI app
        app = FastAPI()
        service.add_to_app(app)

        # Register method handler with decorator
        @service.method("ProcessDocument")
        def process_document(request: CdaRequest) -> CdaResponse:
            # Process the document
            return CdaResponse(
                document="Processed document content",
                error=None
            )
        ```
    """

    def __init__(
        self,
        adapter: Optional[NoteReaderAdapter] = None,
        event_dispatcher: Optional[EventDispatcher] = None,
    ):
        """
        Initialize a new NoteReader service.

        Args:
            adapter: NoteReaderAdapter instance for handling SOAP requests (creates default if None)
            event_dispatcher: Optional EventDispatcher instance
        """
        super().__init__(
            adapter=adapter or NoteReaderAdapter.create(),
            event_dispatcher=event_dispatcher or EventDispatcher(),
        )

    def method(self, method_name: str) -> Callable:
        """
        Decorator to register a handler for a specific SOAP method.

        Args:
            method_name: The SOAP method name to handle (e.g. ProcessDocument)

        Returns:
            Decorator function that registers the handler
        """

        def decorator(handler):
            self.adapter.register_handler(method_name, handler)
            return handler

        return decorator

    def create_wsgi_app(self) -> WsgiApplication:
        """
        Creates a WSGI application for the SOAP service.

        This method sets up the WSGI application with proper SOAP protocol
        configuration and handler registration.

        Returns:
            A configured WsgiApplication ready to mount in FastAPI

        Raises:
            ValueError: If no ProcessDocument handler is registered
        """
        # Get the registered handler for ProcessDocument
        if "ProcessDocument" not in self.adapter._handlers:
            raise ValueError(
                "No ProcessDocument handler registered. "
                "You must register a handler before creating the WSGI app. "
                "Use @service.method('ProcessDocument') to register a handler."
            )

        # Create adapter for SOAP service integration
        def service_adapter(cda_request: CdaRequest) -> CdaResponse:
            # This calls the adapter's handle method to process the request
            try:
                # This will be executed synchronously in the SOAP context
                handler = self.adapter._handlers["ProcessDocument"]
                result = handler(cda_request)
                return self.adapter._process_result(result)
            except Exception as e:
                logger.error(f"Error in SOAP service adapter: {str(e)}")
                return CdaResponse(document="", error=str(e))

        # Assign the service adapter function to CDSServices._service
        CDSServices._service = service_adapter

        # Configure the Spyne application
        application = Application(
            [CDSServices],
            name=self.adapter.config.service_name,
            tns=self.adapter.config.namespace,
            in_protocol=Soap11(validator="lxml"),
            out_protocol=Soap11(),
            classes=[ServerFault, ClientFault],
        )
        # Create WSGI app
        return WsgiApplication(application)

    # TODO: Should be delegated to HealthChainAPI
    def add_to_app(self, app: FastAPI, path: Optional[str] = None) -> None:
        """
        Add this service to a FastAPI application.

        Args:
            app: The FastAPI application to add to
            path: The path to add the SOAP service at

        Note:
            This method creates a WSGI application and adds it to the
            specified FastAPI application at the given path.
        """
        mount_path = path or self.adapter.config.default_mount_path
        wsgi_app = self.create_wsgi_app()
        app.mount(mount_path, WSGIMiddleware(wsgi_app))
        logger.info(f"NoteReader service added at {mount_path}")
