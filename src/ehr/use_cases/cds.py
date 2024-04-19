from pydantic import Dict
from ..base import BaseUseCase, Workflow


class ClinicalDecisionSupport(BaseUseCase):
    """
    Simulates the behaviour of EHR backend for Clinical Decision Support (CDS)
    """
    def _validate_data(self, data, workflow: Workflow) -> bool:
        # do something to valida fhir data and the worklow it's for
        pass

    def construct_request(self, data, workflow: Workflow) -> Dict:
        if self._validate_data(data, workflow):
            # do something to construct a cds rest API post request depending on the workflow
            request = {}
        else:
            raise ValueError(f"Error validating data for workflow {Workflow}")

        return request