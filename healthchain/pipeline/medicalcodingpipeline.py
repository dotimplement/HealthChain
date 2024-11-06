from healthchain.io.cdaconnector import CdaConnector
from healthchain.pipeline.base import BasePipeline, ModelConfig
from healthchain.pipeline.modelrouter import ModelRouter


class MedicalCodingPipeline(BasePipeline):
    """
    A pipeline for medical coding tasks using NLP models.

    This pipeline is configured to process clinical documents using a medical NLP model
    for tasks like named entity recognition and linking (NER+L). It uses CDA format
    for input and output handling.

    Examples:
        >>> # Using with SpaCy/MedCAT
        >>> pipeline = MedicalCodingPipeline.load("medcatlite", source="spacy")
        >>>
        >>> # Using with Hugging Face
        >>> pipeline = MedicalCodingPipeline.load(
        ...     "bert-base-uncased",
        ...     task="ner"
        ... )
        >>> results = pipeline(documents)
    """

    def __init__(self):
        super().__init__()
        self.router = ModelRouter()

    def configure_pipeline(self, config: ModelConfig) -> None:
        """Configure pipeline with CDA connector and NER+L model.

        Args:
            config (ModelConfig): Configuration for the NER+L model
        """
        cda_connector = CdaConnector()
        model = self.router.get_component(config)

        self.add_input(cda_connector)
        self.add_node(model, stage="ner+l")
        self.add_output(cda_connector)
