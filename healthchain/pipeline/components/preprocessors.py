from healthchain.pipeline.components.basecomponent import Component
from healthchain.io.containers import Document
from typing import TypeVar

T = TypeVar("T")


# TODO: implement this class
class TextPreprocessor(Component[str]):
    def __call__(self, doc: Document) -> Document:
        # Example preprocessing: tokenization
        doc.tokens = doc.text.lower().split()
        return doc
