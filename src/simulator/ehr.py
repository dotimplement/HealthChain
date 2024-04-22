import logging
import requests

from pathlib import Path
from typing import Dict
from enum import Enum

from .use_cases.test import TestUseCase
from .base import BaseClient, BaseUseCase, UseCaseType, Workflow

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
    def __init__(self, use_case: BaseUseCase = None) -> None:
        self._use_case = use_case
        self.data = None # DoppelData object; 
        self.fhir_server_endpoint = None  # this is just for reference, simulating return of data from fhir server is all the same
    
    @property
    def UseCase(self) -> UseCaseType:
        return self._use_case.description()
    
    @UseCase.setter
    def UseCase(self, use_case: UseCase) -> None:
        self._use_case = use_case

    # to implement in DoppelData
    @property
    def DataSchema(self) -> Dict:
        if self.data is not None:
            return self.data._schema
        else:
            return None
    
    @classmethod
    def from_doppeldata(cls, data, use_case: UseCase) -> None:
        """
        Constructs EHR from DoppelData object
        """
        return cls(data, use_case)

    @classmethod
    def from_path(cls, path: Path, use_case: UseCase) -> None:
        """
        Constructs EHR from a local folder containing requests
        """
        data = path
        return cls(data, use_case)
    
    def add_database(self, data) -> None:
        """
        This will take in a DoppelData object
        """
        self.data = data

    def send_request(self, url: str, workflow: Workflow) -> None:
        """
        Sends the API request to an AI service
        """
        if self._use_case is None:
            raise RuntimeError("No EHR use case configured! Set using .UseCase")

        response = {}
        request = self._use_case.construct_request(self.data, workflow)
        
        try: 
            response = requests.post(url=url, data=request)
        except Exception as e:
            log.error(f"Error sending request: {e}")
        

        return response
    
    async def send_request_bulk(self, num: int, url: str, workflow: Workflow) -> None:
        """
        Sends bulk API requests to an AI service
        """

