from healthchain.pipeline.base import BasePipeline, ModelConfig
from healthchain.pipeline.mixins import ModelRoutingMixin


class MedicalCodingPipeline(BasePipeline, ModelRoutingMixin):
    """
    Pipeline for extracting and coding medical concepts from clinical documents using NLP models.

    Stages:
        1. NER+L: Extracts and links medical concepts from document text.

    Usage Examples:
        # With SpaCy
        >>> pipeline = MedicalCodingPipeline.from_model_id("en_core_sci_sm", source="spacy")

        # With Hugging Face
        >>> pipeline = MedicalCodingPipeline.from_model_id("bert-base-uncased", task="ner")

        # With LangChain
        >>> chain = ChatPromptTemplate.from_template("Extract medical codes: {text}") | ChatOpenAI()
        >>> pipeline = MedicalCodingPipeline.load(chain)
    """

    def __init__(self):
        BasePipeline.__init__(self)
        ModelRoutingMixin.__init__(self)

    def configure_pipeline(self, config: ModelConfig) -> None:
        """Configure pipeline with NER+L model.

        Args:
            config (ModelConfig): Configuration for the NER+L model
        """
        config.task = "ner"  # set task if hf
        model = self.get_model_component(config)

        self.add_node(model, stage="ner+l")

    def process_request(self, request, adapter=None):
        """
        Process a CDA request and return CDA response using an adapter.

        Args:
            request: CdaRequest object
            adapter: Optional CdaAdapter instance

        Returns:
            CdaResponse: Processed response

        Example:
            >>> pipeline = MedicalCodingPipeline.from_model_id("en_core_sci_sm", source="spacy")
            >>> response = pipeline.process_request(cda_request)  # CdaRequest → CdaResponse
        """
        if adapter is None:
            from healthchain.io import CdaAdapter

            adapter = CdaAdapter()

        doc = adapter.parse(request)
        doc = self(doc)
        return adapter.format(doc)
