import logging
import inspect

from typing import Dict, Optional

from fhir.resources.resource import Resource

from healthchain.service import Service
from healthchain.service.endpoints import Endpoint, ApiProtocol
from healthchain.base import BaseUseCase, BaseStrategy, BaseClient
from healthchain.apimethod import APIMethod
from healthchain.workflows import (
    UseCaseMapping,
    UseCaseType,
    Workflow,
    validate_workflow,
)
from healthchain.models import (
    CDSRequest,
    CDSResponse,
    CDSService,
    CDSServiceInformation,
)
from healthchain.models.hooks import (
    OrderSelectContext,
    OrderSignContext,
    PatientViewContext,
    EncounterDischargeContext,
    Prefetch,
)


log = logging.getLogger(__name__)


class ClinicalDecisionSupportStrategy(BaseStrategy):
    """
    Handles the request construction and validation
    """

    def __init__(self) -> None:
        self.api_protocol = ApiProtocol.rest
        self.context_mapping = {
            Workflow.order_select: OrderSelectContext,
            Workflow.order_sign: OrderSignContext,
            Workflow.patient_view: PatientViewContext,
            Workflow.encounter_discharge: EncounterDischargeContext,
        }

    @validate_workflow(UseCaseMapping.ClinicalDecisionSupport)
    def construct_request(
        self,
        prefetch_data: Dict[str, Resource],
        workflow: Workflow,
        context: Optional[Dict[str, str]] = {},
    ) -> CDSRequest:
        """
        Constructs a HL7-compliant CDS request based on workflow.

        Parameters:
            prefetch_data (Dict[str, Resource]): Dictionary mapping prefetch keys to FHIR resources
            workflow (Workflow): The CDS hook name, e.g. patient-view
            context (Optional[Dict[str, str]]): Optional context data for the CDS hook

        Returns:
            CDSRequest: A Pydantic model that wraps a CDS request for REST API

        Raises:
            ValueError: If the workflow is invalid or not implemented
            TypeError: If any prefetch value is not a valid FHIR resource
        """
        log.debug(f"Constructing CDS request for {workflow.value} from {prefetch_data}")

        context_model = self.context_mapping.get(workflow, None)
        if context_model is None:
            raise ValueError(
                f"Invalid workflow {workflow.value} or workflow model not implemented."
            )
        if not isinstance(prefetch_data, Prefetch):
            raise TypeError(
                f"Prefetch data must be a Prefetch object, but got {type(prefetch_data)}"
            )

        request = CDSRequest(
            hook=workflow.value,
            context=context_model(**context),
            prefetch=prefetch_data.prefetch,
        )

        return request


class ClinicalDecisionSupport(BaseUseCase):
    """
    Implements EHR backend simulator for Clinical Decision Support (CDS)

    Parameters:
        service_api (APIMethod): the function body to inject into the main service
        service_config (Dict): the config kwargs for the uvicorn server passed into service
        service (Service): the service runner object
        client (BaseClient): the client runner object

    See https://cds-hooks.org/ for specification
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
        self._type = UseCaseType.cds
        self._strategy = ClinicalDecisionSupportStrategy()
        # do we need keys? just in case
        # TODO make configurable
        self._endpoints = {
            "info": Endpoint(
                path="/cds-services",
                method="GET",
                function=self.cds_discovery,
                api_protocol="REST",
            ),
            "service_mount": Endpoint(
                path="/cds-services/{id}",
                method="POST",
                function=self.cds_service,
                api_protocol="REST",
            ),
        }

    @property
    def description(self) -> str:
        return "Clinical decision support (HL7 CDS specification)"

    @property
    def type(self) -> UseCaseType:
        return self._type

    @property
    def strategy(self) -> BaseStrategy:
        return self._strategy

    @property
    def endpoints(self) -> Dict[str, Endpoint]:
        return self._endpoints

    def cds_discovery(self) -> CDSServiceInformation:
        """
        CDS discovery endpoint for FastAPI app, should be mounted to /cds-services
        """
        if self._client is None:
            log.warning("CDS 'client' not configured, check class init.")
            return CDSServiceInformation(services=[])

        service_info = CDSService(
            hook=self._client.workflow.value,
            description="A test CDS hook service.",
            id="1",
        )
        return CDSServiceInformation(services=[service_info])

    def cds_service(self, id: str, request: CDSRequest) -> CDSResponse:
        """
        CDS service endpoint for FastAPI app, mounted to /cds-services/{id}

        This method handles the execution of a specific CDS service. It validates the
        service configuration, checks the input parameters, executes the service
        function, and ensures the correct response type is returned.

        Args:
            id (str): The unique identifier of the CDS service to be executed.
            request (CDSRequest): The request object containing the input data for the CDS service.

        Returns:
            CDSResponse: The response object containing the cards generated by the CDS service.

        Raises:
            AssertionError: If the service function is not properly configured.
            TypeError: If the input or output types do not match the expected types.

        Note:
            This method performs several checks to ensure the integrity of the service:
            1. Verifies that the service API is configured.
            2. Validates the signature of the service function.
            3. Ensures the service function accepts a CDSRequest as its first argument.
            4. Verifies that the service function returns a CDSResponse.
        """
        # TODO: can register multiple services and fetch with id

        # Check service_api
        if self._service_api is None:
            log.warning("CDS 'service_api' not configured, check class init.")
            return CDSResponse(cards=[])

        # Check that the first argument of self._service_api.func is of type CDSRequest
        func_signature = inspect.signature(self._service_api.func)
        params = list(func_signature.parameters.values())
        if len(params) < 2:  # Only 'self' parameter
            raise AssertionError(
                "Service function must have at least one parameter besides 'self'"
            )
        first_param = params[1]  # Skip 'self'
        if first_param.annotation == inspect.Parameter.empty:
            log.warning(
                "Service function parameter has no type annotation. Expected CDSRequest."
            )
        elif first_param.annotation != CDSRequest:
            raise TypeError(
                f"Expected first argument of service function to be CDSRequest, but got {first_param.annotation}"
            )

        # Call the service function
        response = self._service_api.func(self, request)

        # Check that response is of type CDSResponse
        if not isinstance(response, CDSResponse):
            raise TypeError(f"Expected CDSResponse, but got {type(response).__name__}")

        return response
