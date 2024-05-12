import logging

from typing import Dict, Callable

from ..base import BaseUseCase, UseCaseMapping, UseCaseType, Workflow, validate_workflow
from ..models.requests.cdsrequest import CDSRequest
from ..models.responses.cdsresponse import CDSResponse
from ..models.hooks.orderselect import OrderSelectContext
from ..models.hooks.ordersign import OrderSignContext
from ..models.hooks.patientview import PatientViewContext
from ..models.hooks.encounterdischarge import EncounterDischargeContext
from ..utils.endpoints import Endpoint
from ..utils.apimethod import APIMethod

log = logging.getLogger(__name__)


class ClinicalDecisionSupport(BaseUseCase):
    """
    Implements EHR backend strategy for Clinical Decision Support (CDS)
    """

    def __init__(self, service_api: APIMethod = None) -> None:
        self.type = UseCaseType.cds
        self.context_mapping = {
            Workflow.order_select: OrderSelectContext,
            Workflow.order_sign: OrderSignContext,
            Workflow.patient_view: PatientViewContext,
            Workflow.encounter_discharge: EncounterDischargeContext,
        }
        # do we need keys? just in case
        self.endpoints = {
            "info": Endpoint(
                path="/cds-services", method="GET", function=self.cds_discovery
            ),
            "service_mount": Endpoint(
                path="/cds-services/{id}", method="POST", function=self.cds_service
            ),
        }
        self._service_api = service_api

    @property
    def service_api(self) -> str:
        if self._service_api is not None:
            return self._service_api.__dict__
        return "api not set"

    @property
    def description(self) -> str:
        return "Clinical decision support (HL7 CDS specification)"

    @service_api.setter
    def service_api(self, func: Callable) -> None:
        self._service_api = func

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

    def cds_discovery(self) -> str:
        return "cds check"

    def cds_service(self, id: str, request: CDSRequest) -> CDSResponse:
        # get json string - could be configurable?
        request_json = request.model_dump_json()

        # TODO: need to get kwargs here
        result = self._service_api.func(self, text=request_json)

        # TODO: could use llm to fix results here?
        return CDSResponse(**result)
