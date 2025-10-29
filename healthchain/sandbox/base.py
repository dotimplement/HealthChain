from abc import ABC, abstractmethod
from typing import Dict
from enum import Enum

from healthchain.models.hooks.prefetch import Prefetch
from healthchain.sandbox.workflows import Workflow


class ApiProtocol(Enum):
    """
    Enum defining the supported API protocols.

    Available protocols:
    - soap: SOAP protocol
    - rest: REST protocol
    """

    soap = "SOAP"
    rest = "REST"


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


class DatasetLoader(ABC):
    """
    Abstract base class for dataset loaders.

    Subclasses should implement the load() method to return Prefetch data
    from their specific dataset source.
    """

    @abstractmethod
    def load(self, **kwargs) -> Prefetch:
        """
        Load dataset and return as Prefetch object.

        Args:
            **kwargs: Loader-specific parameters

        Returns:
            Prefetch object containing FHIR resources

        Raises:
            FileNotFoundError: If dataset files are not found
            ValueError: If dataset parameters are invalid
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Dataset name for registration."""
        pass

    @property
    def description(self) -> str:
        """Optional description of the dataset."""
        return ""
