from abc import ABC, abstractmethod
from enum import Enum
from pydantic import Dict


# a workflow is a specific event that may occur in an EHR that triggers a request to server
class Workflow(Enum):
    patient_view = "patient-view"
    order_select = "order-select"
    order_sign = "order-sign"


class UseCase(Enum):
    clinical_decision_support = "cds"
    clinical_documentation = "notereader"


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

class BaseUseCase(ABC):
    """
    Abstract class for a specific use case of an EHR object
    Use cases will differ by:
    - the data it accepts (FHIR or CDA)
    - the format of the request it constructs (CDS Hook or NoteReader workflows)
    """
    @abstractmethod
    def _validate_data(self, data) -> bool:
        pass

    @abstractmethod
    def construct_request(self, data, workflow: Workflow) -> Dict:
        pass