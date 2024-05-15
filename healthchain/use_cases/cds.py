import logging
import inspect

from typing import Dict, Optional, List

from ..base import (
    BaseUseCase,
    BaseStrategy,
    UseCaseMapping,
    UseCaseType,
    BaseClient,
    Workflow,
    validate_workflow,
)
from ..service.service import Service
from ..models.requests.cdsrequest import CDSRequest
from ..models.responses.cdsresponse import CDSResponse
from ..models.responses.cdsdiscovery import CDSService, CDSServiceInformation
from ..models.hooks.orderselect import OrderSelectContext
from ..models.hooks.ordersign import OrderSignContext
from ..models.hooks.patientview import PatientViewContext
from ..models.hooks.encounterdischarge import EncounterDischargeContext
from ..utils.endpoints import Endpoint
from ..utils.apimethod import APIMethod

log = logging.getLogger(__name__)


class ClinicalDecisionSupportStrategy(BaseStrategy):
    """
    Handles the request construction and validation
    """

    def __init__(self) -> None:
        self.context_mapping = {
            Workflow.order_select: OrderSelectContext,
            Workflow.order_sign: OrderSignContext,
            Workflow.patient_view: PatientViewContext,
            Workflow.encounter_discharge: EncounterDischargeContext,
        }

    def _validate_data(self, data, workflow: Workflow) -> bool:
        # do something to valida fhir data and the worklow it's for
        return True

    @validate_workflow(UseCaseMapping.ClinicalDecisionSupport)
    def construct_request(self, data, workflow: Workflow) -> Dict:
        """
        Constructs a HL7-compliant CDS request based on workflow.

        Parameters:
            data: FHIR data to be injected in request.
            workflow (Workflow): The CDS hook name, e.g. patient-view.

        Returns:
            Dict: A json-compatible CDS request.

        Raises:
            ValueError: If the workflow is invalid or the data does not validate properly.
        """
        # TODO: sub data for actual DoppelData format!!
        if self._validate_data(data, workflow):
            log.debug(f"Constructing CDS request for {workflow.value} from {data}")

            context_model = self.context_mapping.get(workflow, None)
            if context_model is None:
                raise ValueError(
                    f"Invalid workflow {workflow.value} or workflow model not implemented."
                )

            context = context_model(**data.context)
            request = CDSRequest(
                hook=workflow.value, hookInstance=data.uuid, context=context
            )
        else:
            raise ValueError(f"Error validating data for workflow {Workflow}")

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
        self._type = UseCaseType.cds
        self._strategy = ClinicalDecisionSupportStrategy()
        # do we need keys? just in case
        self._endpoints = {
            "info": Endpoint(
                path="/cds-services", method="GET", function=self.cds_discovery
            ),
            "service_mount": Endpoint(
                path="/cds-services/{id}", method="POST", function=self.cds_service
            ),
        }
        self.service_api: APIMethod = service_api
        self.service_config: Dict = service_config
        self.service: Service = service
        self.client: BaseClient = client
        self.responses: List[Dict[str, str]] = []

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
        if self.client is None:
            log.warning("CDS 'client' not configured, check class init.")
            return CDSServiceInformation(services=[])

        service_info = CDSService(
            hook=self.client.workflow.value,
            description="A test CDS hook service.",
            id="1",
        )
        return CDSServiceInformation(services=[service_info])

    def cds_service(self, id: str, request: CDSRequest) -> CDSResponse:
        """
        CDS service endpoint for FastAPI app, should be mounted to /cds-services/{id}
        """
        if self.service_api is None:
            log.warning("CDS 'service_api' not configured, check class init.")
            return CDSResponse(cards=[])

        # TODO: can register multiple services and fetch with id
        request_json = request.model_dump_json()
        signature = inspect.signature(self.service_api.func)
        assert (
            len(signature.parameters) == 2
        ), f"Incorrect number of arguments: {len(signature.parameters)} {signature}; CDS Service functions currently only accept 'self' and a single input argument."

        # TODO: better handling of args/kwargs io
        # params = iter(inspect.signature(self._service_api.func).parameters.items())
        # for name, param in params:
        #     print(name, param, param.annotation)

        result = self.service_api.func(self, request_json)

        # TODO: could use llm to check and fix results here?
        if result is None:
            log.warning(
                "CDS 'service_api' returned None, please check function definition."
            )
            return CDSResponse(cards=[])

        return CDSResponse(**result)
