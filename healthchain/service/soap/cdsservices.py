import logging

from spyne import rpc, Service, Unicode, ByteArray
from typing import Callable

from .models.notereaderresponse import Response


log = logging.getLogger(__name__)


class CDSServices(Service):
    # Ugh WHY did Epic name it like this - I'm not sure if this is something you can change so I will keep it like this
    def __init__(self, service_func: Callable) -> None:
        super().__init__()
        self._service_func = service_func

    @rpc(
        Unicode,
        Unicode,
        Unicode,
        ByteArray,
        _in_arg_names={
            "sessionId": "SessionID",
            "workType": "WorkType",
            "organizationId": "OrganizationID",
            "document": "Document",
        },
        _wsdl_part_name="parameters",
        _returns=Response,
        # _faults=[ClientFault, ServerFault]
    )
    def ProcessDocument(self, ctx, sessionId, workType, organizationId, document):
        # will this work?
        response = self._service_func(document)

        return response
