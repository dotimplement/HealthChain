import logging

from typing import Dict, Optional
from fhir.resources.resource import Resource

from healthchain.service.endpoints import ApiProtocol
from healthchain.sandbox.base import BaseUseCase, BaseRequestConstructor, BaseClient
from healthchain.sandbox.workflows import (
    UseCaseMapping,
    UseCaseType,
    Workflow,
    validate_workflow,
)
from healthchain.models.requests import CDSRequest
from healthchain.models.hooks import (
    OrderSelectContext,
    OrderSignContext,
    PatientViewContext,
    EncounterDischargeContext,
    Prefetch,
)

log = logging.getLogger(__name__)


class CdsRequestConstructor(BaseRequestConstructor):
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
        Constructs a HL7-compliant CDS request with prefetch data.

        Parameters:
            prefetch_data (Dict[str, Resource]): Dictionary mapping prefetch keys to FHIR resources
            workflow (Workflow): The CDS hook name, e.g. patient-view
            context (Optional[Dict[str, str]]): Optional context data for the CDS hook

        Returns:
            CDSRequest: A Pydantic model that wraps a CDS request for REST API

        Raises:
            ValueError: If the workflow is invalid or not implemented
            TypeError: If any prefetch value is not a valid FHIR resource

        # TODO: Add FhirServer support
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
    Implements EHR backend simulator for Clinical Decision Support (CDS).

    This class provides functionality to simulate CDS Hooks interactions between
    an EHR system and a CDS service. It handles the construction and sending of
    CDS Hook requests according to the HL7 CDS Hooks specification.

    Parameters:
        path (str): The API endpoint path for CDS services
        client (Optional[BaseClient]): The client used to send requests to the CDS service

    The class uses a CdsRequestConstructor strategy to build properly formatted
    CDS Hook requests with appropriate context and prefetch data.

    See https://cds-hooks.org/ for the complete specification
    """

    def __init__(
        self,
        path: str = "/cds-services/",
        client: Optional[BaseClient] = None,
    ) -> None:
        super().__init__(
            client=client,
        )
        self._type = UseCaseType.cds
        self._strategy = CdsRequestConstructor()
        self._path = path

    @property
    def description(self) -> str:
        return "Clinical decision support (HL7 CDS specification)"

    @property
    def type(self) -> UseCaseType:
        return self._type

    @property
    def strategy(self) -> BaseRequestConstructor:
        return self._strategy
