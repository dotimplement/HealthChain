import logging

from typing import Dict

from ..base import BaseUseCase, UseCaseMapping, Workflow, validate_workflow
from ..models.requests.cdsrequest import CDSRequest
from ..models.hooks.orderselect import OrderSelectContext
from ..models.hooks.ordersign import OrderSignContext
from ..models.hooks.patientview import PatientViewContext
from ..models.hooks.encounterdischarge import EncounterDischargeContext

log = logging.getLogger(__name__)


class ClinicalDecisionSupport(BaseUseCase):
    """
    Implements EHR backend strategy for Clinical Decision Support (CDS)
    """

    def __init__(self) -> None:
        super().__init__()
        self.context_mapping = {
            Workflow.order_select: OrderSelectContext,
            Workflow.order_sign: OrderSignContext,
            Workflow.patient_view: PatientViewContext,
            Workflow.encounter_discharge: EncounterDischargeContext,
        }

    @property
    def description(self) -> str:
        return "Clinical decision support (HL7 CDS specification)"

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
