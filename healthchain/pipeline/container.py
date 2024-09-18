from typing import Dict, Any, TypeVar, Generic

T = TypeVar("T")


class DataContainer(Generic[T]):
    def __init__(self, data: T):
        self.data = data
        self.metadata: Dict[str, Any] = {}
