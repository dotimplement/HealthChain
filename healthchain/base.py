from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict

from .utils.endpoints import Endpoint


# a workflow is a specific event that may occur in an EHR that triggers a request to server
class Workflow(Enum):
    patient_view = "patient-view"
    order_select = "order-select"
    order_sign = "order-sign"
    encounter_discharge = "encounter-discharge"
    notereader_sign_inpatient = "notereader-sign-inpatient"
    notereader_sign_outpatient = "notereader-sign-outpatient"


class UseCaseType(Enum):
    cds = "ClinicalDecisionSupport"
    clindoc = "ClinicalDocumentation"


class UseCaseMapping(Enum):
    ClinicalDecisionSupport = (
        "patient-view",
        "order-select",
        "order-sign",
        "encounter-discharge",
    )
    ClinicalDocumentation = ("notereader-sign-inpatient", "notereader-sign-outpatient")

    def __init__(self, *workflows):
        self.allowed_workflows = workflows


def is_valid_workflow(use_case: UseCaseMapping, workflow: Workflow) -> bool:
    return workflow.value in use_case.allowed_workflows


def validate_workflow(use_case: UseCaseMapping):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if len(kwargs) > 0:
                workflow = kwargs.get("workflow")
            else:
                for arg in args:
                    if type(arg) == Workflow:
                        workflow = arg
            if not is_valid_workflow(use_case, workflow):
                raise ValueError(f"Invalid workflow {workflow} for UseCase {use_case}")
            return func(*args, **kwargs)

        return wrapper

    return decorator


class BaseClient(ABC):
    """Base client class
    A client can be an EHR or CPOE etc.
    The basic operation is that it sends data in a specified standard.
    """

    @abstractmethod
    def send_request(self) -> None:
        """
        Sends a request to AI service
        """


class BaseStrategy(ABC):
    """
    Abstract class for the strategy for validating and constructing a request
    Use cases will differ by:
    - the data it accepts (FHIR or CDA)
    - the format of the request it constructs (CDS Hook or NoteReader workflows)
    """

    @abstractmethod
    def construct_request(self, data, workflow: Workflow) -> Dict:
        pass


class BaseUseCase(ABC):
    """
    Abstract class for a specific use case of an EHR object
    Use cases will differ by:
    - the data it accepts (FHIR or CDA)
    - the format of the request it constructs (CDS Hook or NoteReader workflows)
    """

    @property
    @abstractmethod
    def type(self) -> UseCaseType:
        pass

    @property
    @abstractmethod
    def strategy(self) -> BaseStrategy:
        pass

    @property
    @abstractmethod
    def endpoints(self) -> Dict[str, Endpoint]:
        pass
