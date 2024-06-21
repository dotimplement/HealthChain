from spyne import Application
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from typing import Callable

from .epiccdsservice import CDSServices


def start_wsgi(
    service: Callable,
    app_name: str = "ICDSServices",
    tns: str = "urn:epic-com:Common.2013.Services",
):
    CDSServices._service = service

    application = Application(
        [CDSServices],
        name=app_name,
        tns=tns,
        in_protocol=Soap11(validator="lxml"),
        out_protocol=Soap11(),
        # classes=[FaultType, ServerFault, ClientFault],
        # documents_container=CustomInterfaceDocuments,
    )

    wsgi_app = WsgiApplication(application)

    return wsgi_app
