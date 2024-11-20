from healthchain.io.cdaconnector import CdaConnector
from healthchain.pipeline.base import BasePipeline, ModelConfig
from healthchain.pipeline.mixins import ModelRoutingMixin


class MedicalCodingPipeline(BasePipeline, ModelRoutingMixin):
    """
    A pipeline for medical coding tasks using NLP models.

    This pipeline processes clinical documents using medical NLP models to extract
    and code medical concepts. It uses CDA format for input/output handling and
    supports named entity recognition and linking (NER+L) to medical ontologies.

    The pipeline consists of the following stages:
    1. Input: CDA connector loads clinical documents
    2. NER+L: Medical NLP model extracts and links medical concepts
    3. Output: Returns coded results via CDA connector

    Examples:
        >>> # Using with SpaCy/MedCAT
        >>> pipeline = MedicalCodingPipeline.from_model_id("medcatlite", source="spacy")
        >>> cda_response = pipeline(documents)
        >>>
        >>> # Using with Hugging Face
        >>> pipeline = MedicalCodingPipeline.from_model_id(
        ...     "bert-base-uncased",
        ...     task="ner"
        ... )
        >>> # Using with LangChain
        >>> chain = ChatPromptTemplate.from_template("Extract medical codes: {text}") | ChatOpenAI()
        >>> pipeline = MedicalCodingPipeline.load(chain)
        >>>
        >>> cda_response = pipeline(documents)
    """

    def __init__(self):
        BasePipeline.__init__(self)
        ModelRoutingMixin.__init__(self)

    def configure_pipeline(self, config: ModelConfig) -> None:
        """Configure pipeline with CDA connector and NER+L model.

        Args:
            config (ModelConfig): Configuration for the NER+L model
        """
        cda_connector = CdaConnector()
        config.task = "ner"  # set task if hf
        model = self.get_model_component(config)

        self.add_input(cda_connector)
        self.add_node(model, stage="ner+l")
        self.add_output(cda_connector)
