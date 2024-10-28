from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from healthchain.io.containers import DataContainer

T = TypeVar("T")


class BaseConnector(Generic[T], ABC):
    """
    Abstract base class for all connectors in the pipeline.

    This class should be subclassed to create specific connectors.
    Subclasses must implement the input and output methods.
    """

    @abstractmethod
    def input(self, data: DataContainer[T]) -> DataContainer[T]:
        """
        Convert input data to the pipeline's internal format.

        Args:
            data (DataContainer[T]): The input data to be converted.

        Returns:
            DataContainer[T]: The converted data.
        """
        pass

    @abstractmethod
    def output(self, data: DataContainer[T]) -> DataContainer[T]:
        """
        Convert pipeline's internal format to output data.

        Args:
            data (DataContainer[T]): The data to be converted for output.

        Returns:
            DataContainer[T]: The converted output data.
        """
        pass
