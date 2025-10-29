"""
MIMIC-on-FHIR dataset loader.

Loads patient data from the MIMIC-IV-on-FHIR dataset for testing and demos.
"""

import logging
import random
from pathlib import Path
from typing import Dict, List, Optional

from fhir.resources.resource import Resource

from healthchain.models import Prefetch
from healthchain.sandbox.datasets import DatasetLoader

log = logging.getLogger(__name__)


class MimicOnFHIRLoader(DatasetLoader):
    """
    Loader for MIMIC-IV-on-FHIR dataset.

    This loader supports loading FHIR resources from the MIMIC-IV dataset
    that has been converted to FHIR format. It can load specific patients,
    sample random patients, or filter by resource types.

    Examples:
        Load a sample of 10 random patients:
        >>> loader = MimicOnFHIRLoader(data_path="path/to/mimic-fhir")
        >>> prefetch = loader.load(sample_size=10)

        Load specific patients:
        >>> prefetch = loader.load(patient_ids=["patient-123", "patient-456"])

        Load with resource filtering:
        >>> prefetch = loader.load(
        ...     sample_size=5,
        ...     resource_types=["Condition", "MedicationRequest"]
        ... )
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize MIMIC-on-FHIR loader.

        Args:
            data_path: Path to MIMIC-on-FHIR data directory. If None, will
                      attempt to find in common locations or environment variables.
        """
        self._data_path = Path(data_path) if data_path else self._find_data_path()

    @property
    def name(self) -> str:
        """Dataset name for registration."""
        return "mimic-on-fhir"

    @property
    def description(self) -> str:
        """Dataset description."""
        return (
            "MIMIC-IV-on-FHIR: Real de-identified clinical data from "
            "Beth Israel Deaconess Medical Center in FHIR format"
        )

    def _find_data_path(self) -> Optional[Path]:
        """
        Attempt to find MIMIC-on-FHIR data in common locations.

        Returns:
            Path to data directory if found, None otherwise
        """
        import os

        # Check environment variable
        env_path = os.getenv("MIMIC_FHIR_PATH")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        # Check common locations
        common_paths = [
            Path.cwd() / "data" / "mimic-fhir",
            Path.home() / "mimic-fhir",
            Path.home() / "data" / "mimic-fhir",
        ]

        for path in common_paths:
            if path.exists():
                log.info(f"Found MIMIC-on-FHIR data at: {path}")
                return path

        log.warning(
            "MIMIC-on-FHIR data path not specified and not found in common locations. "
            "You can set MIMIC_FHIR_PATH environment variable or provide data_path parameter."
        )
        return None

    def load(
        self,
        patient_ids: Optional[List[str]] = None,
        sample_size: Optional[int] = None,
        resource_types: Optional[List[str]] = None,
        random_seed: Optional[int] = None,
        **kwargs,
    ) -> Prefetch:
        """
        Load MIMIC-on-FHIR data as Prefetch object.

        Args:
            patient_ids: Specific patient IDs to load. If provided, sample_size is ignored.
            sample_size: Number of random patients to sample. Defaults to 1 if neither
                        patient_ids nor sample_size is provided.
            resource_types: Filter by specific resource types (e.g., ["Condition", "Observation"]).
                          If None, loads all available resource types.
            random_seed: Random seed for reproducible sampling.
            **kwargs: Additional parameters (reserved for future use)

        Returns:
            Prefetch object containing FHIR resources

        Raises:
            FileNotFoundError: If data path is not set or doesn't exist
            ValueError: If no patients match the criteria
        """
        if self._data_path is None or not self._data_path.exists():
            raise FileNotFoundError(
                f"MIMIC-on-FHIR data not found at: {self._data_path}. "
                "Please provide a valid data_path or set MIMIC_FHIR_PATH environment variable."
            )

        if random_seed is not None:
            random.seed(random_seed)

        # Determine which patients to load
        if patient_ids:
            selected_patients = patient_ids
        else:
            available_patients = self._list_available_patients()
            if not available_patients:
                raise ValueError(f"No patient data found in {self._data_path}")

            sample_size = sample_size or 1
            selected_patients = random.sample(
                available_patients, min(sample_size, len(available_patients))
            )

        log.info(f"Loading {len(selected_patients)} patients from MIMIC-on-FHIR")

        # Load resources for selected patients
        prefetch_data: Dict[str, Resource] = {}

        for patient_id in selected_patients:
            patient_resources = self._load_patient_resources(patient_id, resource_types)
            # Merge resources into prefetch_data
            for resource_type, resource in patient_resources.items():
                if resource_type not in prefetch_data:
                    prefetch_data[resource_type] = resource
                # TODO: Handle merging multiple resources of same type
                # For now, just use the first one

        if not prefetch_data:
            raise ValueError(
                f"No resources found for patients: {selected_patients}. "
                f"Resource types filter: {resource_types}"
            )

        log.info(
            f"Loaded {len(prefetch_data)} resource types: {list(prefetch_data.keys())}"
        )

        return Prefetch(prefetch=prefetch_data)

    def _list_available_patients(self) -> List[str]:
        """
        List all available patient IDs in the dataset.

        Returns:
            List of patient ID strings

        Note:
            This is a placeholder implementation. The actual implementation
            will depend on how MIMIC-on-FHIR data is organized on disk.
            Common organizations:
            - One directory per patient
            - Bundle files with patient ID in filename
            - Single large bundle file
        """
        # TODO: Implement based on actual MIMIC-on-FHIR file structure
        # This is a placeholder that assumes patient directories
        patient_dirs = [
            d.name
            for d in self._data_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        if not patient_dirs:
            # Try looking for bundle files
            bundle_files = list(self._data_path.glob("*.json"))
            # Extract patient IDs from bundle files if present
            # This is highly dependent on MIMIC-on-FHIR file naming conventions
            log.warning(
                "Patient directory structure not found. "
                f"Found {len(bundle_files)} bundle files. "
                "Patient loading may need adjustment based on actual data structure."
            )

        return patient_dirs

    def _load_patient_resources(
        self, patient_id: str, resource_types: Optional[List[str]] = None
    ) -> Dict[str, Resource]:
        """
        Load FHIR resources for a specific patient.

        Args:
            patient_id: Patient identifier
            resource_types: Optional filter for specific resource types

        Returns:
            Dictionary mapping resource type names to Resource objects

        Note:
            This is a placeholder implementation. The actual implementation
            will depend on how MIMIC-on-FHIR data is organized.
        """
        resources = {}

        patient_path = self._data_path / patient_id

        if not patient_path.exists():
            log.warning(f"Patient directory not found: {patient_path}")
            return resources

        # TODO: Implement based on actual MIMIC-on-FHIR file structure
        # Common patterns:
        # 1. Each resource in separate JSON file (resourceType_id.json)
        # 2. Bundle file per patient (patient_id.json)
        # 3. Resource type directories with files (Condition/condition_id.json)

        # Placeholder: Look for JSON files in patient directory
        for json_file in patient_path.glob("*.json"):
            try:
                # This would need proper parsing based on FHIR resource structure
                # For now, just log what we'd process
                log.debug(f"Would load: {json_file}")
                # resource = self._parse_fhir_resource(json_file)
                # if resource_types is None or resource.resource_type in resource_types:
                #     resources[resource.resource_type.lower()] = resource
            except Exception as e:
                log.error(f"Error loading {json_file}: {e}")

        return resources

    def _parse_fhir_resource(self, file_path: Path) -> Resource:
        """
        Parse a FHIR resource from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed FHIR Resource

        Raises:
            ValueError: If file cannot be parsed as FHIR resource
        """
        import json

        with open(file_path, "r") as f:
            data = json.load(f)

        # Determine resource type and parse accordingly
        resource_type = data.get("resourceType")
        if not resource_type:
            raise ValueError(f"No resourceType found in {file_path}")

        # Use fhir.resources to parse based on resource type
        from fhir.resources import get_fhir_model_class

        resource_class = get_fhir_model_class(resource_type)
        return resource_class.parse_obj(data)

    def set_data_path(self, path: Path) -> "MimicOnFHIRLoader":
        """
        Set the data path for the loader.

        Args:
            path: Path to MIMIC-on-FHIR data directory

        Returns:
            Self for method chaining

        Raises:
            FileNotFoundError: If path doesn't exist
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Data path does not exist: {path}")

        self._data_path = path
        log.info(f"Set MIMIC-on-FHIR data path to: {path}")
        return self
