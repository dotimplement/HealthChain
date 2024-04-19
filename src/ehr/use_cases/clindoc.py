from pydantic import Dict
from ..base import BaseUseCase, Workflow


class ClinicalDocumentation(BaseUseCase):
    """
    Simulates the behaviour of EHR backend for clinical documentation (NoteReader)
    """
    def _validate_data(self, data, workflow: Workflow) -> bool:
        # do something to validate cda data and the workflow it's for
        pass

    def construct_request(self, data, workflow: Workflow) -> Dict:
        if self._validate_data(data, workflow):
            # do something to construct a notereader soap request
            request = {}
        else:
            raise ValueError(f"Error validating data for workflow {Workflow}")

        return request