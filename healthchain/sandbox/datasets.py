"""
Dataset registry and loader infrastructure for SandboxClient.

Provides a centralized registry for loading test datasets like MIMIC-on-FHIR and Synthea.
"""

import logging

from typing import Any, Dict, List

from healthchain.sandbox.base import DatasetLoader


log = logging.getLogger(__name__)


class DatasetRegistry:
    """
    Registry for managing available datasets.

    Datasets are registered at import time and can be loaded by name.
    """

    _datasets: Dict[str, DatasetLoader] = {}

    @classmethod
    def register(cls, loader: DatasetLoader) -> None:
        """
        Register a dataset loader.

        Args:
            loader: DatasetLoader instance to register

        Raises:
            ValueError: If dataset name is already registered
        """
        name = loader.name
        if name in cls._datasets:
            log.warning(f"Dataset '{name}' is already registered. Overwriting.")

        cls._datasets[name] = loader
        log.debug(f"Registered dataset: {name}")

    @classmethod
    def load(cls, name: str, data_dir: str, **kwargs) -> Dict:
        """
        Load a dataset by name.

        Args:
            name: Name of the dataset to load
            data_dir: Path to the directory containing dataset files
            **kwargs: Dataset-specific parameters

        Returns:
            Dict containing FHIR resources

        Raises:
            KeyError: If dataset name is not registered
        """
        if name not in cls._datasets:
            raise KeyError(
                f"Dataset '{name}' not found. "
                f"Available datasets: {cls.list_datasets()}"
            )

        loader = cls._datasets[name]
        return loader.load(data_dir=data_dir, **kwargs)

    @classmethod
    def list_datasets(cls) -> List[str]:
        """
        Get list of registered dataset names.

        Returns:
            List of dataset names
        """
        return list(cls._datasets.keys())

    @classmethod
    def get_dataset_info(cls, name: str) -> Dict[str, Any]:
        """
        Get information about a registered dataset.

        Args:
            name: Name of the dataset

        Returns:
            Dictionary with dataset information

        Raises:
            KeyError: If dataset name is not registered
        """
        if name not in cls._datasets:
            raise KeyError(f"Dataset '{name}' not found")

        loader = cls._datasets[name]
        return {
            "name": loader.name,
            "description": loader.description,
            "loader_class": loader.__class__.__name__,
        }

    @classmethod
    def clear(cls) -> None:
        """Clear all registered datasets. Mainly for testing."""
        cls._datasets.clear()


def list_available_datasets() -> Dict[str, str]:
    """
    Get a dictionary of all available datasets with their descriptions.

    This helper function provides an easy way to discover what datasets
    are available in the registry without needing to check documentation.

    Returns:
        Dictionary mapping dataset names to their descriptions

    Example:
        >>> from healthchain.sandbox import list_available_datasets
        >>> datasets = list_available_datasets()
        >>> print(datasets)
        {
            'mimic-on-fhir': 'MIMIC-IV-on-FHIR: Real de-identified clinical data...',
            'synthea-patients': 'Synthea: Synthetic patient data generator...'
        }
    """
    return {
        name: DatasetRegistry.get_dataset_info(name)["description"]
        for name in DatasetRegistry.list_datasets()
    }
