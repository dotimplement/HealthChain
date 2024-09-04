import logging
import inspect

from typing import Dict, Optional

from healthchain.service import Service
from healthchain.models import CdsFhirData
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
    Card,
    CDSService,
    CDSServiceInformation,
)
from healthchain.models.hooks import (
    OrderSelectContext,
    OrderSignContext,
    PatientViewContext,
    EncounterDischargeContext,
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
    def construct_request(self, data: CdsFhirData, workflow: Workflow) -> CDSRequest:
        """
        Constructs a HL7-compliant CDS request based on workflow.

        Parameters:
            data: FHIR data to be injected in request.
            workflow (Workflow): The CDS hook name, e.g. patient-view.

        Returns:
            CDSRequest: A Pydantic model that wraps a CDS request for REST

        Raises:
            ValueError: If the workflow is invalid or the data does not validate properly.
        """
        log.debug(f"Constructing CDS request for {workflow.value} from {data}")

        context_model = self.context_mapping.get(workflow, None)
        if context_model is None:
            raise ValueError(
                f"Invalid workflow {workflow.value} or workflow model not implemented."
            )
        if not isinstance(data, CdsFhirData):
            raise TypeError(
                f"CDS clients must return data of type CdsFhirData, not {type(data)}"
            )

        # i feel like theres a better way to do this
        request_data = data.model_dump()
        request = CDSRequest(
            hook=workflow.value,
            context=context_model(**request_data.get("context", {})),
            prefetch=request_data.get("prefetch"),
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
        CDS service endpoint for FastAPI app, should be mounted to /cds-services/{id}

        Args:
            id (str): The ID of the CDS service.
            request (CDSRequest): The request object containing the input data for the CDS service.

        Returns:
            CDSResponse: The response object containing the cards generated by the CDS service.
        """
        # TODO: can register multiple services and fetch with id

        # Check service_api
        if self._service_api is None:
            log.warning("CDS 'service_api' not configured, check class init.")
            return CDSResponse(cards=[])

        # Check service function signature
        signature = inspect.signature(self._service_api.func)
        assert (
            len(signature.parameters) == 2
        ), f"Incorrect number of arguments: {len(signature.parameters)} {signature}; CDS Service functions currently only accept 'self' and a single input argument."

        # Handle different input types
        service_input = request
        params = iter(inspect.signature(self._service_api.func).parameters.items())
        for name, param in params:
            if name != "self":
                if param.annotation == str:
                    service_input = request.model_dump_json(exclude_none=True)
                elif param.annotation == Dict:
                    service_input = request.model_dump(exclude_none=True)

        # Call the service function
        result = self._service_api.func(self, service_input)

        # Check the result return type
        if result is None:
            log.warning(
                "CDS 'service_api' returned None, please check function definition."
            )
            return CDSResponse(cards=[])

        if not isinstance(result, list):
            if isinstance(result, Card):
                result = [result]
            else:
                raise TypeError(f"Expected a list, but got {type(result).__name__}")

        for card in result:
            if not isinstance(card, Card):
                raise TypeError(
                    f"Expected a list of 'Card' objects, but found an item of type {type(card).__name__}"
                )

        return CDSResponse(cards=result)
