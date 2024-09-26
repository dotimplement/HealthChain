from healthchain.pipeline.components.basecomponent import Component
from healthchain.io.containers import Document
from typing import TypeVar, Generic

T = TypeVar("T")


# TODO: implement this class
class TextPostProcessor(Component[T], Generic[T]):
    def __call__(self, doc: Document) -> Document:
        # Example postprocessing: join tokens back to string
        doc.text = doc.text.replace("OpenAI", "Anthropic")
        doc.text = doc.text.replace("GPT-4", "Claude")

        return doc
