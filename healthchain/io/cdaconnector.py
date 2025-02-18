import logging

from healthchain.io.containers import Document
from healthchain.io.base import BaseConnector
from healthchain.cda_parser import CdaAnnotator
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.fhir import (
    create_bundle,
    set_problem_list_item_category,
    create_document_reference,
)

log = logging.getLogger(__name__)


class CdaConnector(BaseConnector):
    """
    CDAConnector class for handling CDA (Clinical Document Architecture) documents.

    This connector is responsible for parsing CDA documents, extracting relevant
    clinical data, and updating the document with new information. It serves as
    both an input and output connector in the pipeline.

    Attributes:
        overwrite (bool): Flag to determine if existing data should be overwritten
                          when updating the CDA document.
        cda_doc (CdaAnnotator): The parsed CDA document.

    Methods:
        input: Parses the input CDA document and extracts clinical data.
        output: Updates the CDA document with new data and returns the response.
    """

    def __init__(self, overwrite: bool = False):
        self.overwrite = overwrite
        self.cda_doc = None

    def input(self, cda_request: CdaRequest) -> Document:
        """
        Parse the input CDA document and extract clinical data into a HealthChain Document object.

        This method takes a CdaRequest object as input, parses it, and extracts clinical data into a
        FHIR Bundle. It creates two DocumentReference resources:
        1. The original CDA XML document
        2. The extracted note text from the CDA document

        The note text document is linked to the original CDA document through a relationship.
        Continuity of Care Document data (problems, medications, allergies) are also extracted into FHIR resources
        and added to the bundle.

        Args:
            cda_request (CdaRequest): Request object containing the CDA XML document to process.

        Returns:
            Document: A Document object containing:
                - The extracted note text as the document data
                - A FHIR Bundle with:
                    - DocumentReference for the original CDA XML
                    - DocumentReference for the extracted note text
                    - Extracted clinical data as FHIR resources (Condition,
                      MedicationStatement, AllergyIntolerance)

        Note:
            The note text is extracted from the CDA document's note section. If the note
            is a dictionary of sections, they are joined with spaces. If no valid note
            is found, an empty string is used.
        """
        self.cda_doc = CdaAnnotator.from_xml(cda_request.document)

        # Create a FHIR DocumentReference for the original CDA document
        cda_document_reference = create_document_reference(
            data=cda_request.document,
            content_type="text/xml",
            description="Original CDA Document processed by HealthChain",
            attachment_title="Original CDA document in XML format",
        )

        # TODO: Temporary fix for the note section, this might be more of a concern for the Annotator class
        if isinstance(self.cda_doc.note, dict):
            note_text = " ".join(str(value) for value in self.cda_doc.note.values())
        elif isinstance(self.cda_doc.note, str):
            note_text = self.cda_doc.note
        else:
            log.warning("Note section is not a string or dictionary")
            note_text = ""

        # Create a FHIR DocumentReference for the note text
        note_document_reference = create_document_reference(
            data=note_text,
            content_type="text/plain",
            description="Text from note section of related CDA document extracted by HealthChain",
            attachment_title="Note text from the related CDA document",
        )

        doc = Document(data=note_text)

        # Create FHIR Bundle and add documents
        doc.fhir.set_bundle(create_bundle())
        doc.fhir.add_document_reference(cda_document_reference)
        doc.fhir.add_document_reference(
            note_document_reference, parent_id=cda_document_reference.id
        )

        # Set lists with the correct FHIR resources
        doc.fhir.problem_list = self.cda_doc.problem_list
        doc.fhir.medication_list = self.cda_doc.medication_list
        doc.fhir.allergy_list = self.cda_doc.allergy_list

        # Set the category for each problem in the problem list
        for condition in doc.fhir.problem_list:
            set_problem_list_item_category(condition)

        return doc

    def output(self, document: Document) -> CdaResponse:
        """
        Update the CDA document with new data and return the response.

        This method takes a Document object containing updated clinical data,
        updates the CDA document with this new information, and returns a
        CdaResponse object with the updated CDA document.

        Args:
            document (Document): A Document object containing the updated
                                 clinical data (problems, allergies, medications).

        Returns:
            CdaResponse: A response object containing the updated CDA document.

        Note:
            The method updates the CDA document with new problems, allergies,
            and medications if they are present in the input Document object.
            The update behavior (overwrite or append) is determined by the
            `overwrite` attribute of the CdaConnector instance.
        """
        # Update the CDA document with the results from FHIR Bundle
        if document.fhir.problem_list:
            log.debug(
                f"Updating CDA document with {len(document.fhir.problem_list)} problem(s)."
            )
            self.cda_doc.add_to_problem_list(
                document.fhir.problem_list, overwrite=self.overwrite
            )

        # Update allergies
        if document.fhir.allergy_list:
            log.debug(
                f"Updating CDA document with {len(document.fhir.allergy_list)} allergy(ies)."
            )
            self.cda_doc.add_to_allergy_list(
                document.fhir.allergy_list, overwrite=self.overwrite
            )

        # Update medications
        if document.fhir.medication_list:
            log.debug(
                f"Updating CDA document with {len(document.fhir.medication_list)} medication(s)."
            )
            self.cda_doc.add_to_medication_list(
                document.fhir.medication_list, overwrite=self.overwrite
            )

        # Export the updated CDA document
        response_document = self.cda_doc.export()

        return CdaResponse(document=response_document)
