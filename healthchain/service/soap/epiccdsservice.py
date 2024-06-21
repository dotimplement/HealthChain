import logging

from spyne import rpc, ServiceBase, Unicode, ByteArray

from healthchain.models.requests.cdarequest import CdaRequest

from .model.epicresponse import Response


log = logging.getLogger(__name__)


# I'm not happy about this name either but that's what Epic wants
class CDSServices(ServiceBase):
    _service = None

    @rpc(
        Unicode,
        Unicode,
        Unicode,
        ByteArray,
        # NOTE order sensitive
        _in_arg_names={
            "sessionId": "SessionID",
            "workType": "WorkType",
            "organizationId": "OrganizationID",
            "document": "Document",
        },
        _wsdl_part_name="parameters",
        _returns=Response,
        # _faults=[ClientFault, ServerFault]
        # TODO Add faults
    )
    def ProcessDocument(ctx, sessionId, workType, organizationId, document):
        request_document_xml = document[0].decode("UTF-8")

        cda_request = CdaRequest(document=request_document_xml)
        cda_response = ctx.descriptor.service_class._service(cda_request)

        response = Response(
            Document=cda_response.document.encode("UTF-8"), Error=cda_response.error
        )

        return response
