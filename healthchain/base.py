from abc import ABC, abstractmethod
from typing import Dict

from .workflows import UseCaseType, Workflow
from .service.endpoints import Endpoint


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
