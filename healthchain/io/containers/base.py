import json
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, TypeVar


T = TypeVar("T")


@dataclass
class DataContainer(Generic[T]):
    """
    A generic container for data.

    This class represents a container for data with a specific type T.

    Attributes:
        data (T): The data stored in the container.

    Methods:
        to_dict() -> Dict[str, Any]:
            Converts the container's data to a dictionary.

        to_json() -> str:
            Converts the container's data to a JSON string.

        from_dict(cls, data: Dict[str, Any]) -> "DataContainer":
            Creates a DataContainer instance from a dictionary.

        from_json(cls, json_str: str) -> "DataContainer":
            Creates a DataContainer instance from a JSON string.
    """

    data: T

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataContainer":
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "DataContainer":
        return cls.from_dict(json.loads(json_str))


@dataclass
class BaseDocument(DataContainer[str]):
    """Base document container for raw text content."""

    data: str
    text: str = field(init=False)

    def __post_init__(self):
        self.text = self.data

    def char_count(self) -> int:
        return len(self.text)
