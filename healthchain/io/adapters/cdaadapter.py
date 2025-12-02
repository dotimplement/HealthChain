import logging
from typing import Optional

from healthchain.io.containers import Document
from healthchain.io.adapters.base import BaseAdapter
from healthchain.interop import create_interop, FormatType, InteropEngine
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.fhir import (
    create_bundle,
    set_condition_category,
    create_document_reference,
    read_content_attachment,
)
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.documentreference import DocumentReference

log = logging.getLogger(__name__)


class CdaAdapter(BaseAdapter[CdaRequest, CdaResponse]):
    """
    CdaAdapter class for handling CDA (Clinical Document Architecture) documents.

    This adapter facilitates parsing CDA documents into Document objects and formatting
    Document objects back into CDA responses. It uses the InteropEngine to convert
    between CDA and FHIR formats, preserving clinical content while allowing for
    manipulation of the data within HealthChain pipelines.

    Attributes:
        engine (InteropEngine): The interoperability engine for CDA conversions. If not provided, the default engine is used.
        original_cda (str): The original CDA document for use in output.
        note_document_reference (DocumentReference): Reference to the note document
                                                    extracted from the CDA.

    Methods:
        parse: Parses a CDA document and extracts clinical data into a Document.
        format: Converts a Document back to CDA format and returns a CdaResponse.
    """

    def __init__(self, engine: Optional[InteropEngine] = None):
        """
        Initialize CdaAdapter with optional interop engine.

        Args:
            engine (Optional[InteropEngine]): Custom interop engine for CDA conversions.
                                            If None, creates a default engine.
        """
        # Initialize engine with default if not provided
        initialized_engine = engine or create_interop()
        super().__init__(engine=initialized_engine)
        self.engine = initialized_engine
        self.original_cda = None
        self.note_document_reference = None

    def parse(self, cda_request: CdaRequest) -> Document:
        """
        Parse a CDA document and extract clinical data into a HealthChain Document object.

        This method takes a CdaRequest object as input, parses it using the InteropEngine to convert
        CDA to FHIR resources, and creates a Document object with the extracted data. It creates a
        DocumentReference for the original CDA XML and extracts clinical data (problems, medications,
        allergies) into FHIR resources.

        Args:
            cda_request (CdaRequest): Request object containing the CDA XML document to process.

        Returns:
            Document: A Document object containing:
                - The extracted note text as the document data
                - FHIR resources organized into appropriate lists:
                  - problem_list: List of Condition resources
                  - medication_list: List of MedicationStatement resources
                  - allergy_list: List of AllergyIntolerance resources
                - DocumentReference resources for the original CDA and extracted notes

        Note:
            If a DocumentReference resource is found in the converted FHIR resources,
            it is assumed to contain the note text and is stored for later use.
        """
        # Store original CDA for later use
        self.original_cda = cda_request.document

        # Convert CDA to FHIR using the InteropEngine
        fhir_resources = self.engine.to_fhir(
            self.original_cda, src_format=FormatType.CDA
        )

        # Create a FHIR DocumentReference for the original CDA document
        cda_document_reference = create_document_reference(
            data=self.original_cda,
            content_type="text/xml",
            description="Original CDA Document processed by HealthChain",
            attachment_title="Original CDA document in XML format",
        )

        # Extract any DocumentReference resources for notes
        note_text = ""
        doc = Document(data=note_text)  # Create document with empty text initially

        # Create FHIR Bundle and add documents
        doc.fhir.bundle = create_bundle()
        doc.fhir.add_document_reference(cda_document_reference)

        problem_list = []
        medication_list = []
        allergy_list = []

        for resource in fhir_resources:
            if isinstance(resource, Condition):
                problem_list.append(resource)
                set_condition_category(resource, "problem-list-item")
            elif isinstance(resource, MedicationStatement):
                medication_list.append(resource)
            elif isinstance(resource, AllergyIntolerance):
                allergy_list.append(resource)
            elif isinstance(resource, DocumentReference):
                if (
                    resource.content
                    and resource.content[0].attachment
                    and resource.content[0].attachment.data is not None
                ):
                    content = read_content_attachment(resource)
                    if content is not None:
                        note_text = content[0]["data"]
                        self.note_document_reference = resource
                    else:
                        log.warning(
                            f"No content found in DocumentReference: {resource.id}"
                        )

        doc.fhir.problem_list = problem_list
        doc.fhir.medication_list = medication_list
        doc.fhir.allergy_list = allergy_list

        # Update document text
        doc.data = note_text

        # Add the note document reference
        if self.note_document_reference is not None:
            doc.fhir.add_document_reference(
                self.note_document_reference, parent_id=cda_document_reference.id
            )

        return doc

    def format(self, document: Document) -> CdaResponse:
        """
        Convert a Document object back to CDA format and return the response.

        This method takes a Document object containing FHIR resources (problems,
        medications, allergies) and converts them back to CDA format using the
        InteropEngine. It combines all resources from the document's FHIR lists
        and includes the note document reference if available.

        Args:
            document (Document): A Document object containing FHIR resources
                                 in problem_list, medication_list, and allergy_list.

        Returns:
            CdaResponse: A response object containing the CDA document generated
                        from the FHIR resources.
        """
        # Collect all FHIR resources to convert to CDA
        resources = []

        if document.fhir.problem_list:
            resources.extend(document.fhir.problem_list)

        if document.fhir.allergy_list:
            resources.extend(document.fhir.allergy_list)

        if document.fhir.medication_list:
            resources.extend(document.fhir.medication_list)

        # Add the note document reference
        if self.note_document_reference is not None:
            resources.append(self.note_document_reference)

        # Convert FHIR resources to CDA using InteropEngine
        response_document = self.engine.from_fhir(resources, dest_format=FormatType.CDA)

        return CdaResponse(document=response_document)
