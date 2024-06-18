import logging

from typing import Dict

from healthchain.base import BaseUseCase
from healthchain.workflows import (
    UseCaseMapping,
    UseCaseType,
    Workflow,
    validate_workflow,
)

from .apimethod import APIMethod


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

    @validate_workflow(UseCaseMapping.ClinicalDocumentation)
    def construct_request(self, data, workflow: Workflow) -> Dict:
        if self._validate_data(data, workflow):
            # do something to construct a notereader soap request
            log.debug("Constructing Clinical Documentation request...")
            request = {}
        else:
            raise ValueError(f"Error validating data for workflow {Workflow}")

        return request
