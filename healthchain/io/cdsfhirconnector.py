import logging

from healthchain.io.containers import Document
from healthchain.io.baseconnector import Connector
from healthchain.models.data.cdsfhirdata import CdsFhirData
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse

log = logging.getLogger(__name__)


class CdsFhirConnector(Connector):
    """
    CdsFhirConnector class for handling FHIR (Fast Healthcare Interoperability Resources) documents
    for CDS Hooks.

    This connector facilitates the conversion between CDSRequest objects and Document objects,
    as well as the creation of CDSResponse objects from processed Documents.

    Attributes:
        hook_name (str): The name of the CDS Hook being used.
    """

    def __init__(self, hook_name: str):
        self.hook_name = hook_name

    def input(self, in_data: CDSRequest) -> Document:
        """
        Converts a CDSRequest object into a Document object containing FHIR resources.

        This method takes a CDSRequest object as input, extracts the context and prefetch data,
        and creates a CdsFhirData object. It then returns a Document object with the stringified
        prefetch data as the main data content and the CdsFhirData object in the fhir_resources field.

        Args:
            in_data (CDSRequest): The input CDSRequest object containing context and prefetch data.

        Returns:
            Document: A Document object with the following attributes:
                - data: A string representation of the prefetch data.
                - fhir_resources: A CdsFhirData object containing the context and prefetch data.

        Note:
            Future implementations may involve more detailed processing, such as parsing
            notes depending on the hook configuration. This is an area for potential
            future research and development.
        """
        cds_fhir_data = CdsFhirData(context=in_data.context, prefetch=in_data.prefetch)
        return Document(data=str(in_data.prefetch), fhir_resources=cds_fhir_data)

    def output(self, out_data: Document) -> CDSResponse:
        """
        Generates a CDSResponse object from a processed Document object.

        This method takes a Document object that has been processed and potentially
        contains CDS cards and system actions. It creates and returns a CDSResponse
        object based on the contents of the Document.

        Args:
            out_data (Document): A Document object potentially containing CDS cards
                                 and system actions.

        Returns:
            CDSResponse: A response object containing CDS cards and optional system actions.
                         If no cards are found in the Document, an empty list of cards is returned.

        Note:
            - If out_data.cds_cards is None, a warning is logged and an empty list of cards is returned.
            - System actions (out_data.cds_actions) are included in the response if present.
        """
        if out_data.cds_cards is None:
            log.warning("No CDS cards found in Document, returning empty list of cards")
            return CDSResponse(cards=[])

        return CDSResponse(cards=out_data.cds_cards, systemActions=out_data.cds_actions)
