from healthchain.pipeline.base import BasePipeline
from healthchain.pipeline.components import CdsCardCreator
from healthchain.pipeline.modelrouter import ModelConfig
from healthchain.pipeline.mixins import ModelRoutingMixin


class SummarizationPipeline(BasePipeline, ModelRoutingMixin):
    """
    Pipeline for generating summaries from clinical documents using NLP models.

    Stages:
        1. Summarization: Generates summaries from document text.
        2. Card Creation: Formats summaries into CDS Hooks cards.

    Attributes:
        output_template: Template for the output summary (default: "{text}")
        output_template_path: Path to the output template file (default: None)
        delimiter: Delimiter for the output summary (default: "\n")

    Usage Examples:
        >>> pipeline = SummarizationPipeline.from_model_id("facebook/bart-large-cnn", source="huggingface")

        >>> chain = ChatPromptTemplate.from_template("Summarize: {text}") | ChatOpenAI()
        >>> pipeline = SummarizationPipeline.load(chain)
    """

    def __init__(self):
        BasePipeline.__init__(self)
        ModelRoutingMixin.__init__(self)

    def configure_pipeline(self, config: ModelConfig) -> None:
        """Configure pipeline with summarization model and card creator.

        Args:
            config: Model configuration for the summarization model
        """
        config.task = "summarization"
        model = self.get_model_component(config)

        self.add_node(model, stage="summarization")
        self.add_node(
            CdsCardCreator(
                source=config.source.value,
                task="summarization",
                template=self._output_template,  # TODO: assess where this should be configured
                template_path=self._output_template_path,
                delimiter="\n",
            ),
            stage="card-creation",
        )

    def process_request(self, request, hook_name=None, adapter=None):
        """
        Process a CDS request and return CDS response using an adapter.

        Args:
            request: CDSRequest object
            hook_name: CDS hook name for the adapter
            adapter: Optional CdsFhirAdapter instance

        Returns:
            CDSResponse: Processed CDS response with cards

        Example:
            >>> pipeline = SummarizationPipeline.from_model_id("facebook/bart-large-cnn", source="huggingface")
            >>> response = pipeline.process_request(cds_request)  # CDSRequest → CDSResponse
        """
        if adapter is None:
            from healthchain.io import CdsFhirAdapter

            adapter = CdsFhirAdapter(hook_name=hook_name)

        doc = adapter.parse(request)
        doc = self(doc)
        return adapter.format(doc)
