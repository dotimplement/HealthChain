import inspect
import logging
import pkgutil
import xmltodict
import base64

from typing import Dict, Optional

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
from healthchain.apimethod import APIMethod


log = logging.getLogger(__name__)


class ClinicalDocumentationStrategy(BaseStrategy):
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
        This function should wrap FHIR data from CcdFhirData into a template CDA file (dep. vendor
        TODO: implement this function
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
        # TODO: handle different workflows
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

    This class represents the backend strategy for clinical documentation using the NoteReader system.
    It inherits from the `BaseUseCase` class and provides methods for processing NoteReader documents.

    Attributes:
        service_api (Optional[APIMethod]): The service API method to be used for processing the documents.
        service_config (Optional[Dict]): The configuration for the service.
        service (Optional[Service]): The service to be used for processing the documents.
        client (Optional[BaseClient]): The client to be used for communication with the service.
        overwrite (bool): Whether to overwrite existing data in the CDA document.

    """

    def __init__(
        self,
        service_api: Optional[APIMethod] = None,
        service_config: Optional[Dict] = None,
        service: Optional[Service] = None,
        client: Optional[BaseClient] = None,
    ) -> None:
        super().__init__(
            service_api=service_api,
            service_config=service_config,
            service=service,
            client=client,
        )
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
        self.overwrite: bool = False

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
        Process the NoteReader document using the configured service API.

        This method handles the execution of the NoteReader service. It validates the
        service configuration, checks the input parameters, executes the service
        function, and ensures the correct response type is returned.

        Args:
            request (CdaRequest): The request object containing the CDA document to be processed.

        Returns:
            CdaResponse: The response object containing the processed CDA document.

        Raises:
            AssertionError: If the service function is not properly configured.
            TypeError: If the output type does not match the expected CdaResponse type.

        Note:
            This method performs several checks to ensure the integrity of the service:
            1. Verifies that the service API is configured.
            2. Validates the signature of the service function.
            3. Ensures the service function accepts a CdaRequest as its argument.
            4. Verifies that the service function returns a CdaResponse.
        """
        # Check service_api
        if self._service_api is None:
            log.warning("'service_api' not configured, check class init.")
            return CdaResponse(document="")

        # Check service function signature
        signature = inspect.signature(self._service_api.func)
        params = list(signature.parameters.values())
        if len(params) < 2:  # Only 'self' parameter
            raise AssertionError(
                "Service function must have at least one parameter besides 'self'"
            )
        first_param = params[1]  # Skip 'self'
        if first_param.annotation == inspect.Parameter.empty:
            log.warning(
                "Service function parameter has no type annotation. Expected CdaRequest."
            )
        elif first_param.annotation != CdaRequest:
            raise TypeError(
                f"Expected first argument of service function to be CdaRequest, but got {first_param.annotation}"
            )

        # Call the service function
        response = self._service_api.func(self, request)

        # Check return type
        if not isinstance(response, CdaResponse):
            raise TypeError(
                f"Expected return type CdaResponse, got {type(response)} instead."
            )

        return response
