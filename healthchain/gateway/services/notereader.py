"""
SOAP protocol implementation for HealthChain Gateway.

This module provides SOAP integration with healthcare systems, particularly
Epic's CDA document processing services.
"""

from typing import Optional
import logging

from spyne import Application
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware

from healthchain.gateway.core.base import InboundAdapter
from healthchain.gateway.events.dispatcher import EventDispatcher
from healthchain.service.soap.epiccdsservice import CDSServices
from healthchain.models.requests import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.service.soap.model.epicclientfault import ClientFault
from healthchain.service.soap.model.epicserverfault import ServerFault

logger = logging.getLogger(__name__)


class NoteReaderService(InboundAdapter):
    """
    SOAP service implementation for healthcare system integration.

    Provides SOAP integration with healthcare systems, particularly
    Epic's NoteReader CDA document processing and other SOAP-based
    healthcare services.

    Example:
        ```python
        # Create NoteReader service
        note_reader_service = NoteReaderService(
            service_name="ICDSServices",
            namespace="urn:epic-com:Common.2013.Services"
        )

        # Register method handler with decorator
        @note_reader_service.method("ProcessDocument")
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
        event_dispatcher: Optional[EventDispatcher] = None,
        app: Optional[FastAPI] = None,
        mount_path: str = "/notereader",
        **options,
    ):
        """
        Initialize a new NoteReader service.

        Args:
            service_name: The name of the NoteReader service
            namespace: The XML namespace for the NoteReader service
            system_type: The type of system this service connects to
            event_dispatcher: Optional EventDispatcher instance
            app: FastAPI application to mount this service to (optional)
            mount_path: Path to mount the service at (default: "/soap")
            **options: Additional configuration options

        Note:
            The service automatically enables error return and sets up
            event dispatching if not provided.
        """
        options["return_errors"] = True
        super().__init__(**options)
        self.service_name = service_name
        self.namespace = namespace
        self.system_type = system_type
        self.event_dispatcher = event_dispatcher or EventDispatcher()

        # Store app and mount_path for delayed mounting
        self._pending_app = app
        self._pending_mount_path = mount_path

    def method(self, method_name: str):
        """
        Decorator to register a handler for a specific SOAP method.

        Args:
            method_name: The SOAP method name to handle

        Returns:
            Decorator function that registers the handler

        Note:
            This decorator is used to register handlers for SOAP methods.
            The handler function should accept session_id, work_type,
            organization_id, and document parameters.
        """

        def decorator(handler):
            self.register_handler(method_name, handler)

            # Auto-mount if app is pending and this is the ProcessDocument handler
            if method_name == "ProcessDocument" and self._pending_app:
                logger.info(f"Auto-mounting service to {self._pending_mount_path}")
                self.mount_to_app(self._pending_app, self._pending_mount_path)
                # Clear pending app to avoid multiple mounts
                self._pending_app = None

            return handler

        return decorator

    def create_wsgi_app(self) -> WsgiApplication:
        """
        Creates a WSGI application for the SOAP service.

        This method sets up the WSGI application with proper SOAP protocol
        configuration and handler registration. It includes error handling
        and event dispatching capabilities.

        Returns:
            A configured WsgiApplication ready to mount in FastAPI

        Raises:
            ValueError: If no ProcessDocument handler is registered
        """
        # Get the registered handler for ProcessDocument
        handler = self._handlers.get("ProcessDocument")

        if not handler:
            raise ValueError(
                "No ProcessDocument handler registered. "
                "You must register a handler before creating the WSGI app. "
                "Use @service.method('ProcessDocument') to register a handler."
            )

        def service_adapter(cda_request: CdaRequest):
            try:
                logger.debug(f"Processing CDA request with handler {handler}")
                result = handler(cda_request)

                # Dispatch event after successful processing
                # if self.event_dispatcher:
                #     event_data = {
                #         "document_id": getattr(cda_request, "document_id", "default"),
                #         "source_system": self.system_type,
                #         "document_type": "CDA",
                #         "content": cda_request.document,
                #         "result": result
                #     }

                #     Handle async event dispatching
                #     try:
                #         import asyncio
                #         asyncio.get_event_loop().run_until_complete(
                #             self.event_dispatcher.dispatch(
                #                 event_type=EHREventType.DOCUMENT_RECEIVED,
                #                 payload=event_data
                #             )
                #         )
                #     except RuntimeError:
                #         loop = asyncio.new_event_loop()
                #         asyncio.set_event_loop(loop)
                #         loop.run_until_complete(
                #             self.event_dispatcher.dispatch(
                #                 event_type=EHREventType.DOCUMENT_RECEIVED,
                #                 payload=event_data
                #             )
                #         )

                if isinstance(result, CdaResponse):
                    return result
                else:
                    raise ValueError(
                        f"Unexpected result type: {type(result)}. Should be of type CdaResponse"
                    )

            except Exception as e:
                logger.error(f"Error in service adapter: {str(e)}")
                return CdaResponse(document="", error=str(e))

        # Assign the adapter function to CDSServices._service
        CDSServices._service = service_adapter

        # Configure the Spyne application
        application = Application(
            [CDSServices],
            name=self.service_name,
            tns=self.namespace,
            in_protocol=Soap11(validator="lxml"),
            out_protocol=Soap11(),
            classes=[ServerFault, ClientFault],
        )
        # Create WSGI app
        return WsgiApplication(application)

    def mount_to_app(self, app: FastAPI, path: str = "/notereader") -> None:
        """
        Mounts the SOAP service to a FastAPI application.

        Args:
            app: The FastAPI application to mount to
            path: The path to mount the SOAP service at

        Note:
            This method creates a WSGI application and mounts it to the
            specified FastAPI application at the given path.
        """
        wsgi_app = self.create_wsgi_app()
        app.mount(path, WSGIMiddleware(wsgi_app))
        logger.debug(f"SOAP service mounted at {path}")
