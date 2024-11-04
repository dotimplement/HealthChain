from typing import Any
from healthchain.io.cdaconnector import CdaConnector
from healthchain.pipeline.base import BasePipeline
from healthchain.pipeline.modelrouter import ModelRouter


class MedicalCodingPipeline(BasePipeline):
    """
    A pipeline for medical coding tasks using NLP models.

    This pipeline is configured to process clinical documents using a medical NLP model
    for tasks like named entity recognition and linking (NER+L). It uses CDA format
    for input and output handling.

    Examples:
        >>> # Using with SpaCy/MedCAT
        >>> pipeline = MedicalCodingPipeline.load("medcatlite")
        >>>
        >>> # Using with Hugging Face
        >>> pipeline = MedicalCodingPipeline.load(
        ...     "bert-base-uncased",
        ...     task="ner"
        ... )
        >>> results = pipeline(documents)
    """

    def configure_pipeline(self, model_name: str, **model_kwargs: Any) -> None:
        """
        Configure the pipeline with a medical NLP model and CDA connectors.

        Args:
            model_name: Name or path of the model to load
            **model_kwargs: Additional configuration for the model

        Raises:
            ValueError: If no appropriate integration can be found for the model
            ImportError: If required dependencies are not installed
        """
        cda_connector = CdaConnector()

        try:
            model = ModelRouter.get_integration(model_name, **model_kwargs)
        except (ValueError, ImportError) as e:
            raise type(e)(
                f"Failed to configure pipeline with model '{model_name}'. Error: {str(e)}"
            )

        self.add_input(cda_connector)
        self.add_node(model, stage="ner+l")
        self.add_output(cda_connector)
