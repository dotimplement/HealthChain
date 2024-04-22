from typing import Dict

from ..base import BaseUseCase, UseCaseType, Workflow, validate_workflow


class ClinicalDecisionSupport(BaseUseCase):
    """
    Simulates the behaviour of EHR backend for Clinical Decision Support (CDS)
    """
    def description(self) -> str:
        return "Clinical decision support (HL7 CDS specification)"
    
    def _validate_data(self, data, workflow: Workflow) -> bool:
        # do something to valida fhir data and the worklow it's for
        return True
    
    @validate_workflow(UseCaseType.ClinicalDecisionSupport)
    def construct_request(self, data, workflow: Workflow) -> Dict:
        if self._validate_data(data, workflow):
            # do something to construct a cds rest API post request depending on the workflow
            print("Construction CDS request")
            request = {}
        else:
            raise ValueError(f"Error validating data for workflow {Workflow}")

        return request