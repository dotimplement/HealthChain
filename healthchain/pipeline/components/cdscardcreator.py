from healthchain.pipeline.components.base import BaseComponent
from healthchain.io.containers import Document


class CdsCardCreator(BaseComponent[str]):
    def __init__(self):
        pass

    def __call__(self, doc: Document) -> Document:
        return doc
