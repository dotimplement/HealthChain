from healthchain.pipeline.basepipeline import BasePipeline
from healthchain.pipeline.components.preprocessors import TextPreProcessor
from healthchain.pipeline.components.postprocessors import TextPostProcessor
from healthchain.pipeline.components.models import Model


# TODO: Implement this pipeline in full
class MedicalCodingPipeline(BasePipeline):
    def configure_pipeline(self, model_path: str) -> None:
        # Add preprocessing component
        self.add(TextPreProcessor(), stage="preprocessing")

        # Add NER component
        model = Model(model_path)
        self.add(model, stage="ner+l")

        # Add postprocessing component
        self.add(TextPostProcessor(), stage="postprocessing")
