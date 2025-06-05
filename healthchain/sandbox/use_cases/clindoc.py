import base64
import logging
import pkgutil
import xmltodict

from typing import Dict, Optional
from fhir.resources.documentreference import DocumentReference

from healthchain.service.endpoints import ApiProtocol
from healthchain.models import CdaRequest
from healthchain.utils.utils import insert_at_key
from healthchain.sandbox.base import BaseClient, BaseUseCase, BaseRequestConstructor
from healthchain.sandbox.workflows import (
    UseCaseMapping,
    UseCaseType,
    Workflow,
    validate_workflow,
)


log = logging.getLogger(__name__)


class ClinDocRequestConstructor(BaseRequestConstructor):
    """
    Handles the request construction and validation of a NoteReader CDA file
    """

    def __init__(self) -> None:
        self.api_protocol: ApiProtocol = ApiProtocol.soap
        self.soap_envelope: Dict = self._load_soap_envelope()

    def _load_soap_envelope(self):
        data = pkgutil.get_data("healthchain", "templates/soap_envelope.xml")
        return xmltodict.parse(data.decode("utf-8"))

    def construct_cda_xml_document(self):
        """
        This function should wrap FHIR resources from Document into a template CDA file
        TODO: implement this function
        """
        raise NotImplementedError("This function is not implemented yet.")

    @validate_workflow(UseCaseMapping.ClinicalDocumentation)
    def construct_request(
        self, document_reference: DocumentReference, workflow: Workflow
    ) -> CdaRequest:
        """
        Constructs a CDA request for clinical documentation use cases (NoteReader)

        Parameters:
            document_reference (DocumentReference): FHIR DocumentReference containing CDA XML data
            workflow (Workflow): The NoteReader workflow type, e.g. notereader-sign-inpatient

        Returns:
            CdaRequest: A Pydantic model containing the CDA XML wrapped in a SOAP envelope

        Raises:
            ValueError: If the SOAP envelope template is invalid or missing required keys
        """
        # TODO: handle different workflows
        cda_xml = None
        for content in document_reference.content:
            if content.attachment.contentType == "text/xml":
                cda_xml = content.attachment.data
                break

        if cda_xml is not None:
            # Make a copy of the SOAP envelope template
            soap_envelope = self.soap_envelope.copy()

            cda_xml = base64.b64encode(cda_xml).decode("utf-8")

            # Insert encoded cda in the Document section
            if not insert_at_key(soap_envelope, "urn:Document", cda_xml):
                raise ValueError(
                    "Key 'urn:Document' missing from SOAP envelope template!"
                )
            request = CdaRequest.from_dict(soap_envelope)

            return request
        else:
            log.warning("No CDA document found in the DocumentReference!")


class ClinicalDocumentation(BaseUseCase):
    """
    Implements EHR backend strategy for clinical documentation (NoteReader)

    This class represents the backend strategy for clinical documentation using the NoteReader system.
    It inherits from the `BaseUseCase` class and provides methods for processing NoteReader documents.
    When used with the @sandbox decorator, it enables testing and validation of clinical documentation
    workflows in a controlled environment.

    Attributes:
        client (Optional[BaseClient]): The client to be used for communication with the service.
        path (str): The endpoint path to send requests to. Defaults to "/notereader/".
                    Will be normalized to ensure it starts and ends with a forward slash.
        type (UseCaseType): The type of use case, set to UseCaseType.clindoc.
        strategy (BaseRequestConstructor): The strategy used for constructing requests.

    Example:
        @sandbox("http://localhost:8000")
        class MyNoteReader(ClinicalDocumentation):
            def __init__(self):
                super().__init__(path="/custom/notereader/")

        # Create instance and start sandbox
        note_reader = MyNoteReader()
        note_reader.start_sandbox(save_data=True)
    """

    def __init__(
        self,
        path: str = "/notereader/",
        client: Optional[BaseClient] = None,
    ) -> None:
        super().__init__(
            client=client,
        )
        self._type = UseCaseType.clindoc
        self._strategy = ClinDocRequestConstructor()
        self._path = path

    @property
    def description(self) -> str:
        return "Clinical documentation (NoteReader)"

    @property
    def type(self) -> UseCaseType:
        return self._type

    @property
    def strategy(self) -> BaseRequestConstructor:
        return self._strategy
