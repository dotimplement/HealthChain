import logging

from typing import Dict

from ..utils.apimethod import APIMethod
from ..base import BaseUseCase, UseCaseMapping, UseCaseType, Workflow, validate_workflow

log = logging.getLogger(__name__)


# TODO: TO IMPLEMENT
class ClinicalDocumentation(BaseUseCase):
    """
    Implements EHR backend strategy for clinical documentation (NoteReader)
    """

    def __init__(self, service_api: APIMethod = None) -> None:
        self.type = UseCaseType.clindoc
        self.service_api = service_api

    @property
    def description(self) -> str:
        return "Clinical documentation (NoteReader)"

    def _validate_data(self, data, workflow: Workflow) -> bool:
        # do something to validate cda data and the workflow it's for
        return True

    @validate_workflow(UseCaseMapping.ClinicalDocumentation)
    def construct_request(self, data, workflow: Workflow) -> Dict:
        if self._validate_data(data, workflow):
            # do something to construct a notereader soap request
            log.debug("Constructing Clinical Documentation request...")
            request = {}
        else:
            raise ValueError(f"Error validating data for workflow {Workflow}")

        return request
