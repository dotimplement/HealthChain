from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from healthchain.sandbox.workflows import UseCaseType, Workflow


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


class BaseRequestConstructor(ABC):
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
    Abstract base class for healthcare use cases in the sandbox environment.

    This class provides a foundation for implementing different healthcare use cases
    such as Clinical Decision Support (CDS) or Clinical Documentation (NoteReader).
    Subclasses must implement the type and strategy properties.
    """

    def __init__(
        self,
        client: Optional[BaseClient] = None,
    ) -> None:
        self._client: BaseClient = client

        self.responses: List[Dict[str, str]] = []
        self.sandbox_id = None
        self.url = None

    @property
    @abstractmethod
    def type(self) -> UseCaseType:
        pass

    @property
    @abstractmethod
    def strategy(self) -> BaseRequestConstructor:
        pass

    @property
    def path(self) -> str:
        path = self._path
        if not path.startswith("/"):
            path = "/" + path
        if not path.endswith("/"):
            path = path + "/"
        return path
