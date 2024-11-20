import logging

from healthchain.io.containers import Document
from healthchain.io.base import BaseConnector
from healthchain.cda_parser import CdaAnnotator
from healthchain.models.data import CcdData, ConceptLists
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse

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

    def input(self, in_data: CdaRequest) -> Document:
        """
        Parse the input CDA document and extract clinical data.

        This method takes a CdaRequest object containing the CDA document as input,
        parses it using the CdaAnnotator, and extracts relevant clinical data.
        The extracted data is then used to create a CcdData object and a healthchain
        Document object, which is returned.

        Args:
            in_data (CdaRequest): The input request containing the CDA document.

        Returns:
            Document: A Document object containing the extracted clinical data
                      and the original note text.

        """
        self.cda_doc = CdaAnnotator.from_xml(in_data.document)

        # TODO: Temporary fix for the note section, this might be more of a concern for the Annotator class
        if isinstance(self.cda_doc.note, dict):
            note_text = " ".join(str(value) for value in self.cda_doc.note.values())
        elif isinstance(self.cda_doc.note, str):
            note_text = self.cda_doc.note
        else:
            log.warning("Note section is not a string or dictionary")
            note_text = ""

        ccd_data = CcdData(
            concepts=ConceptLists(
                problems=self.cda_doc.problem_list,
                medications=self.cda_doc.medication_list,
                allergies=self.cda_doc.allergy_list,
            ),
            note=note_text,
        )

        doc = Document(data=ccd_data.note)
        doc.hl7.set_ccd_data(ccd_data)

        return doc

    def output(self, out_data: Document) -> CdaResponse:
        """
        Update the CDA document with new data and return the response.

        This method takes a Document object containing updated clinical data,
        updates the CDA document with this new information, and returns a
        CdaResponse object with the updated CDA document.

        Args:
            out_data (Document): A Document object containing the updated
                                 clinical data (problems, allergies, medications).

        Returns:
            CdaResponse: A response object containing the updated CDA document.

        Note:
            The method updates the CDA document with new problems, allergies,
            and medications if they are present in the input Document object.
            The update behavior (overwrite or append) is determined by the
            `overwrite` attribute of the CdaConnector instance.
        """
        # TODO: check what to do with overwrite
        updated_ccd_data = out_data.generate_ccd(overwrite=self.overwrite)

        # Update the CDA document with the results

        if updated_ccd_data.concepts.problems:
            log.debug(
                f"Updating CDA document with {len(updated_ccd_data.concepts.problems)} problem(s)."
            )
            self.cda_doc.add_to_problem_list(
                updated_ccd_data.concepts.problems, overwrite=self.overwrite
            )
        if updated_ccd_data.concepts.allergies:
            log.debug(
                f"Updating CDA document with {len(updated_ccd_data.concepts.allergies)} allergy(ies)."
            )
            self.cda_doc.add_to_allergy_list(
                updated_ccd_data.concepts.allergies, overwrite=self.overwrite
            )
        if updated_ccd_data.concepts.medications:
            log.debug(
                f"Updating CDA document with {len(updated_ccd_data.concepts.medications)} medication(s)."
            )
            self.cda_doc.add_to_medication_list(
                updated_ccd_data.concepts.medications, overwrite=self.overwrite
            )

        # Export the updated CDA document
        response_document = self.cda_doc.export()

        return CdaResponse(document=response_document)
