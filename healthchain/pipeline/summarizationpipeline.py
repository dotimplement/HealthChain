from healthchain.pipeline.base import BasePipeline
from healthchain.io.cdsfhirconnector import CdsFhirConnector
from healthchain.pipeline.components.cdscardcreator import CdsCardCreator
from healthchain.pipeline.modelrouter import ModelRouter, ModelConfig


class SummarizationPipeline(BasePipeline):
    """
    A pipeline for text summarization tasks using NLP models.

    This pipeline is configured to process clinical documents using a summarization model
    to generate concise summaries. It uses CDS FHIR format for input and output handling.

    Examples:
        >>> # Using with GPT model
        >>> pipeline = SummarizationPipeline.load("gpt-4o", source="openai")
        >>>
        >>> # Using with Hugging Face
        >>> pipeline = SummarizationPipeline.load(
        ...     "facebook/bart-large-cnn",
        ...     task="summarization"
        ... )
        >>> summaries = pipeline(documents)
    """

    def __init__(self):
        super().__init__()
        self.router = ModelRouter()

    def configure_pipeline(self, config: ModelConfig) -> None:
        """Configure pipeline with FHIR connector and summarization model.

        Args:
            config: Model configuration for the summarization model
        """
        cds_fhir_connector = CdsFhirConnector(hook_name="encounter-discharge")
        config.config["task"] = "summarization"
        model = self.router.get_component(config)

        self.add_input(cds_fhir_connector)
        self.add_node(model, stage="summarization")
        self.add_node(
            CdsCardCreator(
                source=config.source.value,
                task="summarization",
                template=self._output_template,
            ),
            stage="card-creation",
        )
        self.add_output(cds_fhir_connector)
