from typing import Dict, TypeVar, Generic, List

T = TypeVar("T")


# TODO: Implement data containers
class DataContainer(Generic[T]):
    """
    A generic container for data.

    This class represents a container for data with a specific type T.

    Attributes:
        data (T): The data stored in the container.
    """

    def __init__(self, data: T):
        self.data = data

    def __repr__(self) -> str:
        return f"DataContainer({self.__dict__})"


class Document(DataContainer[str]):
    """
    A container for document data, inheriting from DataContainer.

    This class represents a document with text content and additional
    linguistic features such as tokens, part-of-speech tags, and named entities.

    Attributes:
        text (str): The raw text content of the document.
        tokens (List[str]): A list of individual tokens extracted from the text.
        pos_tags (List[str]): A list of part-of-speech tags corresponding to the tokens.
        entities (List[str]): A list of named entities identified in the text.

    Args:
        data (T): The input data for the document, typically a string containing the text content.
    """

    def __init__(self, data: str):
        super().__init__(data)
        self.text: str = data
        self.tokens: List[str] = []
        self.pos_tags: List[str] = []
        self.entities: List[str] = []

    def __repr__(self) -> str:
        return f"Document({self.__dict__})"


class Tabular(DataContainer[T]):
    """
    A container for tabular data, inheriting from DataContainer.

    This class represents tabular data with columns, indices, and data types.

    Attributes:
        columns (List[str]): A list of column names.
        index (List[int]): A list of indices.
        dtypes (Dict[str, str]): A dictionary of data types for each column.

    Args:
        data (T): The input data for the tabular data, typically a pandas DataFrame.
    """

    def __init__(self, data: T):
        super().__init__(data)
        self.columns: List[str] = []
        self.index: List[int] = []
        self.dtypes: Dict[str, str] = {}

    def __repr__(self) -> str:
        return f"Tabular({self.__dict__})"
