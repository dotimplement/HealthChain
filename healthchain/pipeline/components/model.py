from healthchain.pipeline.components.basecomponent import Component
from healthchain.io.containers import Document
from typing import TypeVar, Generic

T = TypeVar("T")


def load_model(model_path: str):
    # Implement your model loading logic here
    print("Loading model...")


# TODO: implement this class
class Model(Component[T], Generic[T]):
    def __init__(self, model_path: str):
        self.model = load_model(model_path)

    def __call__(self, doc: Document) -> Document:
        # Dummy NER logic for illustration
        doc.entities = [token for token in doc.tokens if token == "openai"]
        return doc
