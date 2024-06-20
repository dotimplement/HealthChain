from spyne import Application
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from .cdsservices import CDSServices


def start_wsgi(service_func):
    application = Application(
        [CDSServices(service_func=service_func)],
        name="ICDSServices",
        tns="urn:epic-com:Common.2013.Services",
        in_protocol=Soap11(validator="lxml"),
        out_protocol=Soap11(),
        # classes=[FaultType, ServerFault, ClientFault],
        # documents_container=CustomInterfaceDocuments,
    )

    wsgi_app = WsgiApplication(application)

    return wsgi_app
