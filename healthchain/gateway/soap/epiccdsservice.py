import logging

from spyne import rpc, ServiceBase, Unicode, ByteArray
from healthchain.models.requests.cdarequest import CdaRequest

from .model import Response, ClientFault, ServerFault


log = logging.getLogger(__name__)


# I'm not happy about this name either but that's what Epic wants
class CDSServices(ServiceBase):
    """
    Represents a CDSServices object that provides methods for processing documents.
    """

    _service = None

    # TODO The _in_arg_names are order sensitive here so need to find a way to make this
    # configurable and easier to catch errors
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
        _faults=[ClientFault, ServerFault],
    )
    def ProcessDocument(ctx, sessionId, workType, organizationId, document):
        """
        Processes a document using the specified session ID, work type, organization ID, and document.

        Args:
            ctx (object): The context object.
            sessionId (str): The session ID.
            workType (str): The work type.
            organizationId (str): The organization ID.
            document (bytes): The document to be processed.

        Returns:
            Response: The response object containing the processed document and any errors.

        Raises:
            ClientFault: If any of the required parameters are missing.
            ServerFault: If there is a server processing error.
            ServerFault: If an unexpected error occurs.
        """
        try:
            if not sessionId:
                raise ClientFault("Missing required parameter: sessionId")
            if not workType:
                raise ClientFault("Missing required parameter: workType")
            if not organizationId:
                raise ClientFault("Missing required parameter: organizationId")
            if not document:
                raise ClientFault("Missing required parameter: document")

            request_document_xml = document[0].decode("UTF-8")

            cda_request = CdaRequest(document=request_document_xml)
            cda_response = ctx.descriptor.service_class._service(cda_request)

            if cda_response.error:
                raise ServerFault(f"Server processing error: {cda_response.error}")

            response = Response(
                Document=cda_response.document.encode("UTF-8"), Error=cda_response.error
            )

            return response

        except ClientFault as e:
            # Re-raise client faults
            raise e
        except ServerFault as e:
            # Re-raise server faults
            raise e
        except Exception as e:
            # Catch all other exceptions and raise as server faults
            raise ServerFault(f"An unexpected error occurred: {str(e)}")
