import logging
from typing import Optional

from fhir.resources.documentreference import DocumentReference

from healthchain.io.containers import Document
from healthchain.io.base import BaseConnector
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse
from healthchain.fhir import read_content_attachment


log = logging.getLogger(__name__)


class CdsFhirConnector(BaseConnector):
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

    def input(
        self, cds_request: CDSRequest, prefetch_document_key: Optional[str] = "document"
    ) -> Document:
        """
        Converts a CDSRequest object into a Document object.

        Takes a CDSRequest containing FHIR resources and extracts them into a Document object.
        The Document will contain all prefetched FHIR resources in its fhir.prefetch_resources.
        If a DocumentReference resource is provided via prefetch_document_key, its text content
        will be extracted into Document.data.

        Args:
            cds_request (CDSRequest): The CDSRequest containing FHIR resources in its prefetch
                and/or a FHIR server URL.
            prefetch_document_key (str, optional): Key in the prefetch data containing a
                DocumentReference resource whose text content should be extracted.
                Defaults to "document".

        Returns:
            Document: A Document object containing:
                - All prefetched FHIR resources in fhir.prefetch_resources
                - Any text content from the DocumentReference in data (empty string if none found)

        Raises:
            ValueError: If neither prefetch nor fhirServer is provided in cds_request
            ValueError: If the prefetch data is invalid or cannot be processed
            NotImplementedError: If fhirServer is provided (FHIR server support not implemented)
        """
        if cds_request.prefetch is None and cds_request.fhirServer is None:
            raise ValueError(
                "Either prefetch or fhirServer must be provided to extract FHIR data!"
            )

        if cds_request.fhirServer is not None:
            raise NotImplementedError("FHIR server is not implemented yet!")

        # Create an empty Document object
        doc = Document(data="")

        # Set the prefetch resources
        doc.fhir.set_prefetch_resources(cds_request.prefetch)

        # Extract text content from DocumentReference resource if provided
        document_resource = cds_request.prefetch.get(prefetch_document_key)
        if not document_resource:
            log.warning(
                f"No DocumentReference resource found in prefetch data with key {prefetch_document_key}"
            )
        elif isinstance(document_resource, DocumentReference):
            try:
                attachments = read_content_attachment(
                    document_resource, include_data=True
                )
                for attachment in attachments:
                    if len(attachments) > 1:
                        doc.data += attachment.get("data", "") + "\n"
                    else:
                        doc.data += attachment.get("data", "")
            except Exception as e:
                log.warning(f"Error extracting text from DocumentReference: {e}")

        return doc

    def output(self, document: Document) -> CDSResponse:
        """
        Convert Document to CDSResponse.

        This method takes a Document object containing CDS cards and actions,
        and converts them into a CDSResponse object that follows the CDS Hooks
        specification.

        Args:
            document (Document): The Document object containing CDS results.

        Returns:
            CDSResponse: A response object containing CDS cards and optional system actions.
                         If no cards are found in the Document, an empty list of cards is returned.
        """
        if document.cds.cards is None:
            log.warning("No CDS cards found in Document, returning empty list of cards")
            return CDSResponse(cards=[])

        return CDSResponse(cards=document.cds.cards, systemActions=document.cds.actions)
