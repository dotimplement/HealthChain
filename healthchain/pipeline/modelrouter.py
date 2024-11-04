from healthchain.pipeline.components.base import BaseComponent
from healthchain.pipeline.components.integrations import (
    SpacyComponent,
    HuggingFaceComponent,
)
import re
from typing import Any


class ModelRouter:
    """
    A router that selects the appropriate integration component based on the model name.
    This is an internal utility class used by pipelines to determine which integration
    to use for a given model.
    """

    @staticmethod
    def get_integration(model_name: str, **kwargs: Any) -> BaseComponent:
        """
        Determine and return the appropriate integration component for the given model.

        Args:
            model_name: Name or path of the model to load
            **kwargs: Additional arguments for the integration component

        Returns:
            An initialized integration component (SpacyComponent, HuggingFaceComponent, etc.)
        """
        # SpaCy models typically follow these patterns
        spacy_patterns = [
            r"^en_core_.*$",  # standard spacy models
            r"^en_core_sci_.*$",  # scispacy models
            r"^.*/spacy/.*$",  # local spacy model paths
            r"^medcatlite$",  # medcat model
        ]

        # Hugging Face models typically include these patterns
        hf_patterns = [
            r"^bert-.*$",
            r"^gpt-.*$",
            r"^t5-.*$",
            r"^distilbert-.*$",
            r".*/huggingface/.*$",
        ]

        # Check for SpaCy models
        for pattern in spacy_patterns:
            if re.match(pattern, model_name):
                return SpacyComponent(model_name)

        # Check for Hugging Face models
        for pattern in hf_patterns:
            if re.match(pattern, model_name):
                return HuggingFaceComponent(
                    model=model_name,
                    task=kwargs.get("task", "text-classification"),
                )

        raise ValueError(
            f"Could not determine appropriate integration for model: {model_name}"
        )
