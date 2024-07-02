from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from healthchain.service.service import Service
from healthchain.service.endpoints import Endpoint

from .workflows import UseCaseType, Workflow
from .apimethod import APIMethod


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

    def __init__(
        self,
        service_api: Optional[APIMethod] = None,
        service_config: Optional[Dict] = None,
        service: Optional[Service] = None,
        client: Optional[BaseClient] = None,
    ) -> None:
        self._service_api: APIMethod = service_api
        self._service: Service = service
        self._client: BaseClient = client

        self.service_config: service_config = service_config
        self.responses: List[Dict[str, str]] = []
        self.sandbox_id = None
        self.url = None

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
