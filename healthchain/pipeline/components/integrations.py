from healthchain.io.containers import Document
from healthchain.pipeline.components.basecomponent import BaseComponent


class SpacyComponent(BaseComponent[str]):
    def __init__(self, path_to_pipeline: str):
        import spacy

        nlp = spacy.load(path_to_pipeline)
        self.nlp = nlp

    def __call__(self, doc: Document) -> Document:
        spacy_doc = self.nlp(doc.data)
        doc.add_spacy_doc(spacy_doc)
        return doc


class HuggingFaceComponent(BaseComponent[str]):
    def __init__(self, task, model):
        from transformers import pipeline

        nlp = pipeline(task=task, model=model)
        self.nlp = nlp
        self.task = task

    def __call__(self, doc: Document) -> Document:
        output = self.nlp(doc.data)
        doc.add_huggingface_output(self.task, output)
        return doc


class LangChainComponent(BaseComponent[str]):
    def __init__(self, chain):
        self.chain = chain

    def __call__(self, doc: Document) -> Document:
        # TODO: These components run on doc.data instead of doc.text (which will be present if spacy has been run)
        # I can see data and text getting confused. Just have one?
        output = self.chain.invoke(doc.data)
        # TODO: Add an optional run_id or value to uniquely distinguish pipeline run (also logging)
        doc.add_langchain_output("chain_output", output)
        return doc
