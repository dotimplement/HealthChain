from healthchain.io.containers import Document
from basecomponent import BaseComponent


class SpacyComponent(BaseComponent[str]):
    @classmethod
    def from_spacy(cls, path_to_pipeline: str) -> "SpacyComponent":
        try:
            import spacy
        except ImportError:
            raise ImportError(
                "Spacy is not installed. Install it with 'pip install your_package_name[spacy]'"
            )

        nlp = spacy.load(path_to_pipeline)
        return cls(nlp)

    def __init__(self, nlp):
        self.nlp = nlp

    def __call__(self, data: Document) -> Document:
        doc = self.nlp(data.data)

        processed_data = {
            "original_text": data.data,
            "tokens": [token.text for token in doc],
            "entities": [(ent.text, ent.label_) for ent in doc.ents],
            "pos_tags": [(token.text, token.pos_) for token in doc],
        }

        # TODO: I'm returning a new document object instead of appending metadata to the input
        return Document(processed_data)


class HuggingFaceComponent(BaseComponent[str]):
    @classmethod
    def from_pretrained(cls, task: str, model: str) -> "HuggingFaceComponent":
        try:
            from transformers import pipeline
        except ImportError:
            raise ImportError(
                "Transformers is not installed. Install it with 'pip install your_package_name[huggingface]'"
            )

        nlp = pipeline(task=task, model=model)
        return cls(nlp, task)

    def __init__(self, pipeline, task):
        self.pipeline = pipeline
        self.task = task

    def __call__(self, data: Document) -> Document:
        results = self.pipeline(data.data)

        processed_data = {
            "original_text": data.data,
            "task": self.task,
            "results": results,
        }

        return Document(processed_data)
