from enum import Enum
from pydantic import List, Optional

# a workflow is a specific event that may occur in an EHR that triggers a request to server
class Workflow(Enum):
    pass

class UseCase(Enum):
    clinical_decision_support = "cds"
    clinical_documentation = "notereader"

class Vendor(Enum):
    Epic = "epic"
    


class EHR:
    """
    EHR mocker which simulates the behaviour of an EHR sending API requests to a third-party server
    Currently support:
    - Clinical Decision Support (HL7 CDS Hooks)
    - Clinical Documentation (Epic NoteReader)
    """
    def __init__(self, data, use_case: UseCase, vendor: Optional[Vendor] = "epic") -> None:
        self.data = data # DoppelData object
        self.vendor = vendor
        self.use_case = use_case
        self.events: List[Workflow]  # the sequence of events is determined by the use case

    def _init_ehr_events() -> None:
        pass
    
    def _construct_request() -> None:
        """
        Constructs the API request using DoppelData object
        """
        pass

    def send_request(num=1) -> None:
        """
        Sends the API request to the NLP service
        """
        pass
