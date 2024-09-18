from typing import Generic, TypeVar

from healthchain.pipeline.container import DataContainer

T = TypeVar("T")


class Component(Generic[T]):
    def __call__(self, data: DataContainer[T]) -> DataContainer[T]:
        return data
