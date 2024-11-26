from healthchain.pipeline.base import BasePipeline
from healthchain.pipeline.components import CdsCardCreator
from healthchain.pipeline.modelrouter import ModelConfig
from healthchain.pipeline.mixins import ModelRoutingMixin
from healthchain.io import CdsFhirConnector


class SummarizationPipeline(BasePipeline, ModelRoutingMixin):
    """
    A pipeline for text summarization tasks using NLP models.

    This pipeline processes clinical documents using a summarization model to generate
    concise summaries. It uses CDS FHIR format for input/output handling and creates
    CDS Hooks cards containing the generated summaries.

    The pipeline consists of the following stages:
    1. Input: CDS FHIR connector loads clinical documents
    2. Summarization: NLP model generates summaries
    3. Card Creation: Formats summaries into CDS Hooks cards
    4. Output: Returns cards via CDS FHIR connector

    Examples:
        >>> # Using with GPT model
        >>> pipeline = SummarizationPipeline.from_model_id("gpt-4o", source="openai")
        >>> cds_response = pipeline(documents)
        >>>
        >>> # Using with Hugging Face
        >>> pipeline = SummarizationPipeline.from_model_id(
        ...     "facebook/bart-large-cnn",
        ...     task="summarization"
        ... )
        >>> cds_response = pipeline(documents)
    """

    def __init__(self):
        BasePipeline.__init__(self)
        ModelRoutingMixin.__init__(self)

    def configure_pipeline(self, config: ModelConfig) -> None:
        """Configure pipeline with FHIR connector and summarization model.

        Args:
            config: Model configuration for the summarization model
        """
        cds_fhir_connector = CdsFhirConnector(hook_name="encounter-discharge")
        config.task = "summarization"
        model = self.get_model_component(config)

        self.add_input(cds_fhir_connector)
        self.add_node(model, stage="summarization")
        self.add_node(
            CdsCardCreator(
                source=config.source.value,
                task="summarization",
                template=self._output_template,
                template_path=self._output_template_path,
                delimiter="\n",
            ),
            stage="card-creation",
        )
        self.add_output(cds_fhir_connector)
