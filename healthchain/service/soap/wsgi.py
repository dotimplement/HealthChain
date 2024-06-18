from spyne import Application
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from .icdsservices import ICDSServices


def start_wsgi():
    application = Application(
        [ICDSServices],
        name="ICDSServices",
        tns="urn:epic-com:Common.2013.Services",
        in_protocol=Soap11(validator="lxml"),
        out_protocol=Soap11(),
        # classes=[FaultType, ServerFault, ClientFault],
        # documents_container=CustomInterfaceDocuments,
    )

    wsgi_app = WsgiApplication(application)

    return wsgi_app
