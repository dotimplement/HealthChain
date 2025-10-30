"""
MIMIC-on-FHIR dataset loader.

Loads patient data from the MIMIC-IV-on-FHIR dataset for testing and demos.
"""

import logging
import random
from pathlib import Path
from typing import Dict, List, Optional

from fhir.resources.R4B.bundle import Bundle

from healthchain.sandbox.datasets import DatasetLoader

log = logging.getLogger(__name__)


class MimicOnFHIRLoader(DatasetLoader):
    """
    Loader for MIMIC-IV-on-FHIR dataset.

    This loader supports loading FHIR resources from the MIMIC-IV dataset
    that has been converted to FHIR format. It can load specific patients,
    sample random patients, or filter by resource types.

    Examples:
        Load via SandboxClient:
        >>> client = SandboxClient(...)
        >>> client.load_from_registry(
        ...     "mimic-on-fhir",
        ...     data_path="./data/mimic-fhir",
        ...     resource_types=["MimicMedication", "MimicCondition"],
        ...     sample_size=10
        ... )
    """

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

    def load(
        self,
        data_path: str,
        resource_types: Optional[List[str]] = None,
        sample_size: Optional[int] = None,
        random_seed: Optional[int] = None,
        **kwargs,
    ) -> Dict:
        """
        Load MIMIC-on-FHIR data as dict containing R4B Bundles.

        Args:
            data_path: Path to MIMIC-on-FHIR data directory
            resource_types: List of MIMIC resource types to load (e.g., ["MimicMedication", "MimicCondition"]).
                          These should match the MIMIC-on-FHIR filename format (without .ndjson.gz extension).
                          If None, raises ValueError.
            sample_size: Number of resources to randomly sample per resource type.
                        If None, loads all available resources.
            random_seed: Random seed for reproducible sampling.
            **kwargs: Additional parameters (reserved for future use)

        Returns:
            Dict containing R4B Bundle resources grouped by FHIR resource type.
            Each Bundle contains resources of the same type.
            Example: {"MedicationStatement": Bundle(...), "Condition": Bundle(...)}

        Raises:
            FileNotFoundError: If data path doesn't exist or resource files not found
            ValueError: If resource_types is None or empty, or if resource validation fails
        """
        data_path = Path(data_path)
        if not data_path.exists():
            raise FileNotFoundError(
                f"MIMIC-on-FHIR data not found at: {data_path}. "
                "Please provide a valid data_path."
            )

        if not resource_types:
            raise ValueError(
                "resource_types parameter is required. "
                "Provide a list of MIMIC resource types to load (e.g., ['MimicMedication', 'MimicCondition'])."
            )

        # Set random seed if provided
        if random_seed is not None:
            random.seed(random_seed)

        # Load resources and group by FHIR resource type
        resources_by_type: Dict[str, List[Dict]] = {}

        for resource_type in resource_types:
            try:
                resources = self._load_resource_file(
                    data_path, resource_type, sample_size
                )

                # Group by FHIR resourceType (not filename)
                for resource in resources:
                    fhir_type = resource["resourceType"]
                    if fhir_type not in resources_by_type:
                        resources_by_type[fhir_type] = []
                    resources_by_type[fhir_type].append(resource)

                log.info(
                    f"Loaded {len(resources)} resources from {resource_type}.ndjson.gz"
                )
            except FileNotFoundError as e:
                log.error(f"Failed to load {resource_type}: {e}")
                raise
            except Exception as e:
                log.error(f"Error loading {resource_type}: {e}")
                raise ValueError(f"Failed to load {resource_type}: {e}")

        if not resources_by_type:
            raise ValueError(
                f"No valid resources loaded from specified resource types: {resource_types}"
            )

        bundles = {}
        for fhir_type, resources in resources_by_type.items():
            bundles[fhir_type] = Bundle(
                type="collection",
                entry=[{"resource": resource} for resource in resources],
            )

        return bundles

    def _load_resource_file(
        self, data_path: Path, resource_type: str, sample_size: Optional[int] = None
    ) -> List[Dict]:
        """
        Load resources from a single MIMIC-on-FHIR .ndjson.gz file.

        Args:
            data_path: Path to MIMIC-on-FHIR data directory
            resource_type: MIMIC resource type (e.g., "MimicMedication")
            sample_size: Number of resources to randomly sample

        Returns:
            List of resource dicts

        Raises:
            FileNotFoundError: If the resource file doesn't exist
            ValueError: If no valid resources found
        """
        import gzip
        import json

        # Construct file path
        fhir_dir = data_path / "fhir"
        file_path = fhir_dir / f"{resource_type}.ndjson.gz"

        if not file_path.exists():
            raise FileNotFoundError(
                f"Resource file not found: {file_path}. "
                f"Expected MIMIC-on-FHIR file at {fhir_dir}/{resource_type}.ndjson.gz"
            )

        # Read all resources from file as dicts
        resources = []
        line_num = 0

        with gzip.open(file_path, "rt") as f:
            for line in f:
                line_num += 1
                try:
                    data = json.loads(line)

                    if not data.get("resourceType"):
                        log.warning(
                            f"Skipping line {line_num} in {resource_type}.ndjson.gz: "
                            "No resourceType field found"
                        )
                        continue

                    resources.append(data)

                except json.JSONDecodeError as e:
                    log.warning(
                        f"Skipping malformed JSON at line {line_num} in {resource_type}.ndjson.gz: {e}"
                    )
                    continue

        if not resources:
            raise ValueError(
                f"No valid resources found in {file_path}. "
                "File may be empty or contain only invalid resources."
            )

        # Apply random sampling if requested
        if sample_size is not None and sample_size < len(resources):
            resources = random.sample(resources, sample_size)

        return resources
