import logging

from healthchain.io.containers import Document
from healthchain.io.base import BaseConnector
from healthchain.interop import create_interop, FormatType
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.fhir import (
    create_bundle,
    set_problem_list_item_category,
    create_document_reference,
    read_content_attachment,
)
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.documentreference import DocumentReference

log = logging.getLogger(__name__)


class CdaConnector(BaseConnector):
    """
    CDAConnector class for handling CDA (Clinical Document Architecture) documents.

    This connector is responsible for parsing CDA documents, extracting relevant
    clinical data, and updating the document with new information. It serves as
    both an input and output connector in the pipeline.

    The connector uses the InteropEngine to convert between CDA and FHIR formats,
    preserving the clinical content while allowing for manipulation of the data
    within the HealthChain pipeline.

    Attributes:
        engine (InteropEngine): The interoperability engine for CDA conversions.
        original_cda (str): The original CDA document for use in output.
        note_document_reference (DocumentReference): Reference to the note document
                                                    extracted from the CDA.

    Methods:
        input: Parses the input CDA document and extracts clinical data.
        output: Updates the CDA document with new data and returns the response.
    """

    def __init__(self, config_dir: str = None):
        self.engine = create_interop(config_dir=config_dir)
        self.original_cda = None
        self.note_document_reference = None

    def input(self, cda_request: CdaRequest) -> Document:
        """
        Parse the input CDA document and extract clinical data into a HealthChain Document object.

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
                - DocumentReference resources for the original CDA and extracted notes with a parent-child relationship

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
                set_problem_list_item_category(resource)
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

    def output(self, document: Document) -> CdaResponse:
        """
        Convert FHIR resources back to CDA format and return the response.

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
