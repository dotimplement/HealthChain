from abc import ABC, abstractmethod

from healthchain.interop.config_manager import InteropConfigManager


class BaseParser(ABC):
    """
    Abstract base class for parsers that convert healthcare data formats.
    """

    def __init__(self, config: InteropConfigManager):
        self.config = config

    @abstractmethod
    def from_string(self, data: str) -> dict:
        """
        Parse input data and convert it to a structured format.
        This method should be implemented by subclasses to handle specific formats.
        Args:
            data: The input data as a string

        Returns:
            A dictionary containing the parsed data structure
        """
        pass
