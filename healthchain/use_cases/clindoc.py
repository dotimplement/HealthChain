import logging
import importlib
import xmltodict
import base64

from typing import Dict, List, Optional

from healthchain.base import BaseClient, BaseUseCase, BaseStrategy
from healthchain.service import Service
from healthchain.service.endpoints import Endpoint, ApiProtocol
from healthchain.utils.utils import insert_at_key
from healthchain.workflows import (
    UseCaseMapping,
    UseCaseType,
    Workflow,
    validate_workflow,
)
from healthchain.models import CdaRequest, CdaResponse, CcdData
from healthchain.cda_parser import CdaAnnotator

from .apimethod import APIMethod


log = logging.getLogger(__name__)


class ClinicalDocumentationStrategy(BaseStrategy):
    """
    Handles the request construction and validation of a NoteReader CDA file
    """

    def __init__(self) -> None:
        self.api_protocol: ApiProtocol = ApiProtocol.soap
        self.soap_envelope: Dict = self._load_soap_envelope()

    def _load_soap_envelope(self):
        path = importlib.resources.files("healthchain.templates") / "soap_envelope.xml"

        with open(path, "r") as file:
            soap_envelope_template = xmltodict.parse(file.read())

        return soap_envelope_template

    def construct_cda_xml_document(self):
        """
        This function should wrap FHIR data from CcdFhirData into a template CDA file (dep. vendor
        """
        pass

    @validate_workflow(UseCaseMapping.ClinicalDocumentation)
    def construct_request(self, data: CcdData, workflow: Workflow) -> CdaRequest:
        """
        Constructs a CDA request for clinical documentation use cases (NoteReader)

        Parameters:
            data: CDA data to be injected in the request
            workflow (Workflow): The NoteReader workflow type, e.g. notereader-sign-inpatient

        Returns:
            CdaRequest: A Pydantic model that wraps CDA data for SOAP request

        Raises:
            ValueError: If the workflow is invalid or the data does not validate properly.
        """
        # TODO: handle converting fhir data from data generator to cda
        if data.cda_xml is not None:
            # Encode the cda xml in base64
            encoded_xml = base64.b64encode(data.cda_xml.encode("utf-8")).decode("utf-8")
            # Make a copy of the SOAP envelope template
            soap_envelope = self.soap_envelope.copy()
            # Insert encoded cda in the Document section
            if not insert_at_key(soap_envelope, "urn:Document", encoded_xml):
                raise ValueError(
                    "Key 'urn:Document' missing from SOAP envelope template!"
                )
            request = CdaRequest.from_dict(soap_envelope)

            return request
        else:
            log.warning(
                "Data generation methods for CDA documents not implemented yet!"
            )


class ClinicalDocumentation(BaseUseCase):
    """
    Implements EHR backend strategy for clinical documentation (NoteReader)
    """

    # TODO: maybe add these attributes to BaseUseCase so don't have to copy and paste for every use case
    def __init__(
        self,
        service_api: Optional[APIMethod] = None,
        service_config: Optional[Dict] = None,
        service: Optional[Service] = None,
        client: Optional[BaseClient] = None,
    ) -> None:
        self._type = UseCaseType.clindoc
        self._strategy = ClinicalDocumentationStrategy()
        self._endpoints = {
            "service_mount": Endpoint(
                path="/notereader/",
                method="POST",
                function=self.process_notereader_document,
                api_protocol="SOAP",
            )
        }
        self._service_api: APIMethod = service_api
        self._service: Service = service
        self._client: BaseClient = client

        self.service_config: service_config = service_config
        self.responses: List[Dict[str, str]] = []
        self.sandbox_id = None
        self.url = None

    @property
    def description(self) -> str:
        return "Clinical documentation (NoteReader)"

    @property
    def type(self) -> UseCaseType:
        return self._type

    @property
    def strategy(self) -> BaseStrategy:
        return self._strategy

    @property
    def endpoints(self) -> Dict[str, Endpoint]:
        return self._endpoints

    def process_notereader_document(self, request: CdaRequest) -> CdaResponse:
        """
        NoteReader endpoint
        """
        cda_doc = CdaAnnotator.from_xml(request.document)
        ccd_data = CcdData(
            problems=cda_doc.problem_list,
            medications=cda_doc.medication_list,
            allergies=cda_doc.allergy_list,
            note=cda_doc.note,
        )
        result = self._service_api.func(self, ccd_data)

        cda_doc.add_to_problem_list(result.problems, overwrite=True)
        cda_doc.add_to_allergy_list(result.allergies, overwrite=True)
        cda_doc.add_to_medication_list(result.medications, overwrite=True)

        response_document = cda_doc.export()

        response = CdaResponse(document=response_document)

        return response
