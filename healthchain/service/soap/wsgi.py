from spyne import Application
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from typing import Callable

from .epiccdsservice import CDSServices
from .model import ClientFault, ServerFault

# TODO: make namespace configurable


def start_wsgi(
    service: Callable,
    app_name: str = "ICDSServices",
    tns: str = "urn:epic-com:Common.2013.Services",
):
    """
    Starts the WSGI application for the SOAP service.

    Args:
        service (Callable): The service function to be used.
        app_name (str, optional): The name of the application. Defaults to "ICDSServices".
        tns (str, optional): The target namespace for the SOAP service. Defaults to "urn:epic-com:Common.2013.Services".

    Returns:
        WsgiApplication: The WSGI application for the SOAP service.
    """
    CDSServices._service = service

    application = Application(
        [CDSServices],
        name=app_name,
        tns=tns,
        in_protocol=Soap11(validator="lxml"),
        out_protocol=Soap11(),
        classes=[ServerFault, ClientFault],
        # documents_container=CustomInterfaceDocuments,
    )

    wsgi_app = WsgiApplication(application)

    return wsgi_app
