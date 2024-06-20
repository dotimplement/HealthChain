import logging
import importlib

from typing import Dict, List, Optional

from healthchain.base import BaseClient, BaseUseCase, BaseStrategy
from healthchain.service import Service
from healthchain.service.endpoints import Endpoint, ApiProtocol
from healthchain.workflows import (
    UseCaseMapping,
    UseCaseType,
    Workflow,
    validate_workflow,
)
from healthchain.models import CdaRequest, CdaResponse, CcdData

from .apimethod import APIMethod


log = logging.getLogger(__name__)


class ClinicalDocumentationStrategy(BaseStrategy):
    """
    Handles the request construction and validation of a NoteReader CDA file
    """

    def __init__(self) -> None:
        self.api_protocol = ApiProtocol.soap
        self.soap_envelope_template = self._load_soap_envelope()

    def _load_soap_envelope(self):
        path = importlib.resources.files("healthchain.templates") / "soap_envelope.xml"

        with open(path, "r") as file:
            soap_envelope_template = file.read()

        return soap_envelope_template

    def construct_cda_xml_document(self):
        """
        This function should wrap FHIR data from CcdFhirData into a template CDA file (dep. vendor)"""
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
            # NOTE This should be base64 encoded. for readability we'll skip this for now
            soap_request = self.soap_envelope_template.replace(
                "<!-- Your XML content here -->", data.cda_xml
            )
            return CdaRequest(document=soap_request)
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
                path="/notereader",
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
        pass
