from healthchain.pipeline.components.base import Component
from healthchain.io.containers import Document
from typing import TypeVar, Generic

T = TypeVar("T")


# TODO: implement this class
class LLM(Component[T], Generic[T]):
    def __init__(self, model_name: str):
        self.model = model_name

    def load_model(self):
        pass

    def load_chain(self):
        pass

    def __call__(self, doc: Document) -> Document:
        return doc
