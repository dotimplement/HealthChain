from healthchain.pipeline.components.basecomponent import Component
from healthchain.io.containers import Document
from typing import TypeVar, Generic

T = TypeVar("T")


# TODO: implement this class
class TextPreprocessor(Component[T], Generic[T]):
    def __call__(self, doc: Document[T]) -> Document[T]:
        # Example preprocessing: tokenization
        doc.tokens = doc.text.lower().split()
        return doc
