import base64
import inspect
import logging
import pkgutil
import xmltodict

from typing import Dict, Optional

from fhir.resources.documentreference import DocumentReference

from healthchain.service import Service
from healthchain.service.endpoints import Endpoint, ApiProtocol
from healthchain.utils.utils import insert_at_key
from healthchain.sandbox.base import BaseClient, BaseUseCase, BaseRequestConstructor
from healthchain.sandbox.apimethod import APIMethod
from healthchain.sandbox.workflows import (
    UseCaseMapping,
    UseCaseType,
    Workflow,
    validate_workflow,
)
from healthchain.models import CdaRequest, CdaResponse


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

    Attributes:
        service_api (Optional[APIMethod]): The service API method to be used for processing the documents.
        service_config (Optional[Dict]): The configuration for the service.
        service (Optional[Service]): The service to be used for processing the documents.
        client (Optional[BaseClient]): The client to be used for communication with the service.

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
        self._strategy = ClinDocRequestConstructor()
        self._endpoints = {
            "service_mount": Endpoint(
                path="/notereader/",
                method="POST",
                function=self.process_notereader_document,
                api_protocol="SOAP",
            )
        }

    @property
    def description(self) -> str:
        return "Clinical documentation (NoteReader)"

    @property
    def type(self) -> UseCaseType:
        return self._type

    @property
    def strategy(self) -> BaseRequestConstructor:
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
