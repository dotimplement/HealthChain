from healthchain.pipeline.base import BasePipeline, ModelConfig
from healthchain.pipeline.mixins import ModelRoutingMixin
from healthchain.pipeline.components import FHIRProblemListExtractor


class MedicalCodingPipeline(BasePipeline, ModelRoutingMixin):
    """
    Pipeline for extracting and coding medical concepts from clinical documents using NLP models.
    Only extracts conditions to problems list for now.

    Stages:
        1. NER+L: Extracts and links medical concepts from document text.
        2. Problem Extraction (last): Converts medical entities to FHIR problem list.

    Attributes:
        extract_problems: Whether to automatically extract FHIR problem list (default: True)
        patient_ref: Patient reference for created conditions (default: "Patient/123")
        code_attribute: Name of the spaCy extension attribute containing medical codes (default: "cui")

    Usage Examples:
        >>> pipeline = MedicalCodingPipeline.from_model_id("en_core_sci_sm", source="spacy")

        >>> pipeline = MedicalCodingPipeline.from_model_id("bert-base-uncased", task="ner")

        >>> chain = ChatPromptTemplate.from_template("Extract medical codes: {text}") | ChatOpenAI()
        >>> pipeline = MedicalCodingPipeline.load(chain)
    """

    def __init__(
        self,
        extract_problems: bool = True,
        patient_ref: str = "Patient/123",
        code_attribute: str = "cui",
    ):
        """
        Initialize MedicalCodingPipeline.

        Args:
            extract_problems: Whether to automatically extract FHIR problem list (default: True)
            patient_ref: Patient reference for created conditions (default: "Patient/123")
            code_attribute: Name of the spaCy extension attribute containing medical codes (default: "cui")
        """
        BasePipeline.__init__(self)
        ModelRoutingMixin.__init__(self)
        self.extract_problems = extract_problems
        self.patient_ref = patient_ref
        self.code_attribute = code_attribute

    def configure_pipeline(self, config: ModelConfig) -> None:
        """Configure pipeline with NER+L model and optional problem extraction.

        Args:
            config (ModelConfig): Configuration for the NER+L model
        """
        config.task = "ner"  # set task if hf
        model = self.get_model_component(config)

        self.add_node(model, stage="ner+l")

        # Automatically add problem list extraction by default
        if self.extract_problems:
            self.add_node(
                FHIRProblemListExtractor(
                    patient_ref=self.patient_ref, code_attribute=self.code_attribute
                ),
                stage="problem-extraction",
                position="last",
            )

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
