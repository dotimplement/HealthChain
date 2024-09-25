from healthchain.pipeline.basepipeline import BasePipeline
from healthchain.io.containers import Document
from healthchain.pipeline.components.preprocessors import TextPreprocessor
from healthchain.pipeline.components.postprocessors import TextPostProcessor
from healthchain.pipeline.components.models import MedCATModel


class MedicalCodingPipeline(BasePipeline):
    def configure_pipeline(self, model_path: str) -> None:
        # Add preprocessing component
        self.add(TextPreprocessor(), stage="preprocessing")

        # Add NER component
        model = MedCATModel(model_path)
        self.add(model, stage="ner+l")

        # Add postprocessing component
        self.add(TextPostProcessor(), stage="postprocessing")


# Usage
pipeline = MedicalCodingPipeline.load("./path/to/model")
nlp = pipeline.build()
text_input = "OpenAI released GPT-4 in 2023."
result = nlp(Document(text_input))
print(f"Processed Text: {result.text}")
print(f"Tokens: {result.tokens}")
print(f"Entities: {result.entities}")
