import logging
import requests

from typing import Dict
from enum import Enum
from pydantic import List, Optional

from .base import BaseClient, UseCase, Workflow

log = logging.getLogger(__name__)


# wrap vendor specific logic in decorators? may be too complex, use config?
class Vendor(Enum):
    Epic = "epic"


class EHR(BaseClient):
    """
    EHR mocker which simulates the behaviour of an EHR sending API requests to a third-party server
    Currently support:
    - Clinical Decision Support (HL7 CDS Hooks)
    - Clinical Documentation (Epic NoteReader)
    """
    def __init__(self, use_case: UseCase) -> None:
        self._use_case = use_case
        self.data = None # DoppelData object; 
        self.fhir_server_endpoint = None  # this is just for reference, simulating return of data from fhir server is all the same
    
    @property
    def UseCase(self) -> UseCase:
        return self._use_case
    
    @UseCase.setter
    def UseCase(self, use_case: UseCase) -> None:
        self._use_case = use_case

    # to implement in DoppelData
    @property
    def DataSchema(self) -> Dict:
        return self.data._schema

    def add_database(self, data) -> None:
        """
        This will take in a DoppelData object and validate it for the appropriate workflow
        """
        self.data = data

    def send_request(self, url: str, workflow: Workflow) -> None:
        """
        Sends the API request to an AI service
        """

        request = self._use_case.construct_request(self.data, workflow)
        
        try: 
            response = requests.post(url=url, body=request)
        except Exception as e:
            raise RuntimeError(f"Error sending request: {e}")
        

        return response

