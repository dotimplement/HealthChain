from healthchain.io.cdaconnector import CdaConnector
from healthchain.pipeline.basepipeline import Pipeline
from healthchain.pipeline.components.preprocessors import TextPreProcessor
from healthchain.pipeline.components.postprocessors import TextPostProcessor
from healthchain.pipeline.components.models import Model


# TODO: Implement this pipeline in full
class MedicalCodingPipeline(Pipeline):
    def configure_pipeline(self, model_path: str) -> None:
        cda_connector = CdaConnector()
        self.add_input(cda_connector)
        # Add preprocessing component
        self.add(TextPreProcessor(), stage="preprocessing")

        # Add NER component
        model = Model(
            model_path
        )  # TODO: should converting the CcdData be a model concern?
        self.add(model, stage="ner+l")

        # Add postprocessing component
        self.add(TextPostProcessor(), stage="postprocessing")
        self.add_output(cda_connector)
