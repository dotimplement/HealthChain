import logging
from typing import Optional, Any

from fhir.resources.documentreference import DocumentReference

from healthchain.io.containers import Document
from healthchain.io.adapters.base import BaseAdapter
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse
from healthchain.fhir import read_content_attachment, convert_prefetch_to_fhir_objects

log = logging.getLogger(__name__)


class CdsFhirAdapter(BaseAdapter[CDSRequest, CDSResponse]):
    """
    CdsFhirAdapter class for handling FHIR (Fast Healthcare Interoperability Resources) documents
    for CDS Hooks.

    This adapter facilitates the conversion between CDSRequest objects and Document objects,
    as well as the creation of CDSResponse objects from processed Documents. Unlike CdaAdapter,
    this adapter works directly with FHIR data and does not require interop conversion.

    Attributes:
        hook_name (str): The name of the CDS Hook being used.
        engine (Optional[Any]): Optional interoperability engine (not used by this adapter).

    Methods:
        parse: Converts a CDSRequest object into a Document object.
        format: Converts a Document object into a CDSResponse object.
    """

    def __init__(self, hook_name: str = None, engine: Optional[Any] = None):
        """
        Initialize CdsFhirAdapter with hook name and optional engine.

        Args:
            hook_name (str): The name of the CDS Hook being used. Defaults to None.
            engine (Optional[Any]): Optional interoperability engine (not used by this adapter).
        """
        super().__init__(engine=engine)
        self.hook_name = hook_name

    def parse(
        self, cds_request: CDSRequest, prefetch_document_key: Optional[str] = "document"
    ) -> Document:
        """
        Convert a CDSRequest object into a Document object.

        Takes a CDSRequest containing FHIR resources and extracts them into a Document object.
        The Document will contain all prefetched FHIR resources in its fhir.prefetch_resources.
        If a DocumentReference resource is provided via prefetch_document_key, its text content
        will be extracted into Document.data. For multiple attachments, the text content will be
        concatenated with newlines.

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
                - For multiple attachments, text content is concatenated with newlines

        Raises:
            ValueError: If neither prefetch nor fhirServer is provided in cds_request
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

        # Convert prefetch dict resources to FHIR objects
        doc.fhir.prefetch_resources = convert_prefetch_to_fhir_objects(
            cds_request.prefetch or {}
        )

        # Extract text content from DocumentReference resource if provided
        document_resource = doc.fhir.prefetch_resources.get(prefetch_document_key)

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

    def format(self, document: Document) -> CDSResponse:
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
