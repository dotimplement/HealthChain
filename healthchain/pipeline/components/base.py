from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from healthchain.io.containers import DataContainer

T = TypeVar("T")


class BaseComponent(Generic[T], ABC):
    """
    Abstract base class for all components in the pipeline.

    This class should be subclassed to create specific components.
    Subclasses must implement the __call__ method.

    Attributes:
        None
    """

    @abstractmethod
    def __call__(self, data: DataContainer[T]) -> DataContainer[T]:
        """
        Process the input data and return the processed data.

        Args:
            data (DataContainer[T]): The input data to be processed.

        Returns:
            DataContainer[T]: The processed data.
        """
        pass


class Component(BaseComponent[T]):
    """
    A concrete implementation of the BaseComponent class.

    This class can be used as a base for creating specific components
    that do not require any additional processing logic.

    Methods:
        __call__(data: DataContainer[T]) -> DataContainer[T]:
            Process the input data and return the processed data.
            In this implementation, the input data is returned unmodified.
    """

    def __call__(self, data: DataContainer[T]) -> DataContainer[T]:
        return data
