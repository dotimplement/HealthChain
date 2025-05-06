"""
SOAP protocol implementation for HealthChain Gateway.

This module provides SOAP integration with healthcare systems, particularly
Epic's CDA document processing services.
"""

from typing import Dict, Any, Callable, List
import logging

from spyne import Application, ServiceBase
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

from healthchain.gateway.core.base import ProtocolService
from healthchain.gateway.events.dispatcher import EventDispatcher, EHREventType


logger = logging.getLogger(__name__)


class SOAPService(ProtocolService):
    """
    SOAP service implementation using the decorator pattern.

    Provides SOAP integration with healthcare systems, particularly
    Epic's NoteReader CDA document processing and other SOAP-based
    healthcare services.

    Example:
        ```python
        # Create SOAP service
        soap_service = SOAPService(
            service_name="ICDSServices",
            namespace="urn:epic-com:Common.2013.Services"
        )

        # Register method handler with decorator
        @soap_service.method("ProcessDocument")
        def process_cda_document(session_id, work_type, organization_id, document):
            # Process the document
            return {
                "document": "Processed document content",
                "error": None
            }
        ```
    """

    def __init__(
        self,
        service_name: str = "ICDSServices",
        namespace: str = "urn:epic-com:Common.2013.Services",
        system_type: str = "EHR_CDA",
        **options,
    ):
        """
        Initialize a new SOAP service.

        Args:
            service_name: The name of the SOAP service
            namespace: The XML namespace for the SOAP service
            system_type: The type of system this service connects to
            **options: Additional configuration options
        """
        super().__init__(**options)
        self.service_name = service_name
        self.namespace = namespace
        self.system_type = system_type
        self.event_dispatcher = options.get("event_dispatcher", EventDispatcher())

    def method(self, method_name: str):
        """
        Decorator to register a handler for a specific SOAP method.

        Args:
            method_name: The SOAP method name to handle

        Returns:
            Decorator function that registers the handler
        """

        def decorator(handler):
            self.register_handler(method_name, handler)
            return handler

        return decorator

    def register_handler(self, method_name: str, handler: Callable):
        """
        Register a handler function for a specific SOAP method.

        Args:
            method_name: The SOAP method name to handle
            handler: Function that will process the method call
        """
        self._handlers[method_name] = handler
        return self

    def handle(self, operation: str, **params) -> Any:
        """
        Process a SOAP method request using registered handlers.

        Args:
            operation: The SOAP method name to invoke
            **params: Parameters for the SOAP method

        Returns:
            Result of the SOAP method call
        """
        # Use registered handler if available
        if operation in self._handlers:
            return self._handlers[operation](**params)

        # Fall back to default handler
        return self._default_handler(operation, **params)

    def _default_handler(self, operation: str, **params) -> Any:
        """
        Default handler for methods without registered handlers.

        Args:
            operation: The SOAP method name
            **params: Method parameters

        Returns:
            Default error response
        """
        logger.warning(f"No handler registered for SOAP method: {operation}")
        return {"error": f"Unsupported method: {operation}"}

    async def process_document(self, document: Dict[str, Any]) -> Any:
        """
        Process a CDA document and emit an event.

        Args:
            document: CDA document as a dictionary

        Returns:
            Processing result
        """
        logger.info("Processing CDA document via SOAP service")

        # Handle with the ProcessDocument method if registered
        if "ProcessDocument" in self._handlers:
            session_id = document.get("session_id", "unknown")
            work_type = document.get("work_type", "unknown")
            organization_id = document.get("organization_id", "unknown")
            doc_content = document.get("document", "")

            result = self._handlers["ProcessDocument"](
                session_id=session_id,
                work_type=work_type,
                organization_id=organization_id,
                document=doc_content,
            )

            # Emit event
            if self.event_dispatcher:
                event_data = {
                    "document_id": document.get("id", "unknown"),
                    "result": result,
                }
                await self.event_dispatcher.dispatch(
                    event_type=EHREventType.DOCUMENT_RECEIVED, payload=event_data
                )

            return result

        # Fall back to default
        return self._default_handler("ProcessDocument", document=document)

    def create_soap_service_class(self) -> type:
        """
        Creates a dynamic SOAP service class based on Epic's requirements.

        Returns:
            A Spyne ServiceBase subclass configured for Epic integration
        """
        handlers = self._handlers

        # Define the SOAP service class
        class DynamicSOAPService(ServiceBase):
            @classmethod
            def process_document(cls, session_id, work_type, organization_id, document):
                """Epic-compatible SOAP method for processing CDA documents"""
                try:
                    if not all([session_id, work_type, organization_id, document]):
                        return {"Error": "Missing required parameters"}

                    # Decode document bytes to string
                    document_xml = (
                        document[0].decode("UTF-8")
                        if isinstance(document[0], bytes)
                        else document[0]
                    )

                    # Process with registered function or default handler
                    if "ProcessDocument" in handlers:
                        response = handlers["ProcessDocument"](
                            session_id=session_id,
                            work_type=work_type,
                            organization_id=organization_id,
                            document=document_xml,
                        )
                    else:
                        # Default processing if no custom processor
                        response = {"document": "Processed document", "error": None}

                    # Return in format expected by Epic
                    return {
                        "Document": response.get("document", "").encode("UTF-8")
                        if isinstance(response.get("document"), str)
                        else b"",
                        "Error": response.get("error"),
                    }

                except Exception as e:
                    logger.error(f"Error processing document: {str(e)}")
                    return {"Error": f"Server error: {str(e)}"}

        # Add other methods dynamically based on registered handlers
        for method_name, handler in handlers.items():
            if method_name != "ProcessDocument":
                setattr(DynamicSOAPService, method_name, handler)

        return DynamicSOAPService

    def create_wsgi_app(self) -> WsgiApplication:
        """
        Creates a WSGI application for the SOAP service.

        Returns:
            A configured WsgiApplication ready to mount in FastAPI
        """
        service_class = self.create_soap_service_class()

        # Configure the Spyne application
        application = Application(
            [service_class],
            name=self.service_name,
            tns=self.namespace,
            in_protocol=Soap11(validator="lxml"),
            out_protocol=Soap11(),
        )

        # Create WSGI app
        return WsgiApplication(application)

    def mount_to_app(self, app: FastAPI, path: str = "/soap") -> None:
        """
        Mounts the SOAP service to a FastAPI application.

        Args:
            app: The FastAPI application to mount to
            path: The path to mount the SOAP service at
        """
        wsgi_app = self.create_wsgi_app()
        app.mount(path, WSGIMiddleware(wsgi_app))
        logger.info(f"SOAP service mounted at {path}")

    def get_capabilities(self) -> List[str]:
        """
        Get list of supported SOAP methods.

        Returns:
            List of method names this service supports
        """
        return list(self._handlers.keys())
