import logging
from typing import Optional

from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.gateway.soap.utils.model import Response, ClientFault, ServerFault

log = logging.getLogger(__name__)


class CDSServices:
    """
    Spyne-free version of the CDSServices SOAP logic.

    - No ServiceBase
    - No @rpc decorator
    - No Spyne types (Unicode, ByteArray)
    - No Spyne argument name mapping
    - No Spyne faults (we raise our own ClientFault / ServerFault directly)

    This class now exposes a normal Python method:
        CDSServices.process_document(...)
    """

    # your user-defined function must be assigned to this externally
    _service = None

    @staticmethod
    def ProcessDocument(
        session_id: Optional[str],
        work_type: Optional[str],
        organization_id: Optional[str],
        document: Optional[bytes],
    ) -> Response:
        """
        Pure Python version of the old Spyne ProcessDocument handler.
        """

        try:
            # === Validate required parameters (same behavior as Spyne) ===
            if not session_id:
                raise ClientFault("Missing required parameter: sessionId")
            if not work_type:
                raise ClientFault("Missing required parameter: workType")
            if not organization_id:
                raise ClientFault("Missing required parameter: organizationId")
            if not document:
                raise ClientFault("Missing required parameter: document")

            # If document used to be a list (Spyne behavior), handle gracefully
            if isinstance(document, (list, tuple)):
                document = document[0]

            # Spyne gave you bytes; we keep same behavior
            request_document_xml = (
                document.decode("utf-8")
                if isinstance(document, bytes)
                else str(document)
            )

            # Build CdaRequest (just like old Spyne path)
            cda_request = CdaRequest(document=request_document_xml)

            # Call the user-provided callback (same behavior as before)
            cda_response = CDSServices._service(cda_request)

            # Error case
            if cda_response.error:
                raise ServerFault(f"Server processing error: {cda_response.error}")

            # Build Response (identical to spyne version)
            return Response(
                Document=cda_response.document.encode("utf-8")
                if isinstance(cda_response.document, str)
                else cda_response.document,
                Error=cda_response.error,
            )

        except ClientFault:
            raise
        except ServerFault:
            raise
        except Exception as exc:
            raise ServerFault(f"An unexpected error occurred: {str(exc)}")
