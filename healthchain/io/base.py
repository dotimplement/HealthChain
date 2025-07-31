from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Any
from healthchain.io.containers import Document

RequestType = TypeVar("RequestType")
ResponseType = TypeVar("ResponseType")


class BaseAdapter(Generic[RequestType, ResponseType], ABC):
    """
    Abstract base class for all adapters in HealthChain.

    Adapters handle conversion between external healthcare data formats
    (CDA, CDS Hooks, etc.) and HealthChain's internal Document objects.

    This class should be subclassed to create specific adapters.
    Subclasses must implement the parse and format methods.
    """

    def __init__(self, engine: Optional[Any] = None):
        """
        Initialize BaseAdapter with optional interop engine.

        Args:
            engine (Optional[Any]): Optional interoperability engine for format conversions.
                                   Only used by adapters that require format conversion (e.g., CDA).
        """
        self.engine = engine

    @abstractmethod
    def parse(self, request: RequestType) -> Document:
        """
        Parse external format data into HealthChain's internal Document format.

        Args:
            request (RequestType): The external format request to be parsed.

        Returns:
            Document: The parsed data as a Document object.
        """
        pass

    @abstractmethod
    def format(self, document: Document) -> ResponseType:
        """
        Format HealthChain's internal Document into external format response.

        Args:
            document (Document): The Document object to be formatted.

        Returns:
            ResponseType: The formatted response in external format.
        """
        pass


# Legacy connector class for backwards compatibility
class BaseConnector(Generic[RequestType], ABC):
    """
    DEPRECATED: Use BaseAdapter instead.

    Abstract base class for legacy connectors.
    """

    @abstractmethod
    def input(self, data: RequestType) -> Document:
        """
        DEPRECATED: Use BaseAdapter.parse() instead.
        """
        pass

    @abstractmethod
    def output(self, data: Document) -> ResponseType:
        """
        DEPRECATED: Use BaseAdapter.format() instead.
        """
        pass
