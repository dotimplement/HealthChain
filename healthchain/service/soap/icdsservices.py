import logging

from spyne import rpc, Service, Unicode, ByteArray
from typing import Callable


log = logging.getLogger(__name__)


class ICDSServices(Service):
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
        # _returns=Response
        # _faults=[ClientFault, ServerFault]
    )
    def ProcessDocument(ctx, sessionId, workType, organizationId, document):
        # will this work?
        # response = ctx._service_func(document)

        pass
