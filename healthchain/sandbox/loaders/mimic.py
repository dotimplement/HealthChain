"""
MIMIC-on-FHIR dataset loader.

Loads patient data from the MIMIC-IV-on-FHIR dataset for testing and demos.
"""

import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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
        ...     data_dir="./data/mimic-fhir",
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
        data_dir: str,
        resource_types: Optional[List[str]] = None,
        sample_size: Optional[int] = None,
        random_seed: Optional[int] = None,
        as_dict: bool = False,
        **kwargs,
    ) -> Union[Dict[str, Bundle], Dict[str, Any]]:
        """
        Load MIMIC-on-FHIR data as FHIR Bundle(s).

        Args:
            data_dir: Path to root MIMIC-on-FHIR directory (expects a /fhir subdir with .ndjson.gz files)
            resource_types: Resource type names to load (e.g., ["MimicMedication"]). Required.
            sample_size: Number of resources to randomly sample per type (loads all if None)
            random_seed: Seed for sampling
            as_dict: If True, return single bundle dict (fast, no validation - for ML workflows).
                If False, return dict of validated Bundle objects grouped by resource type (for CDS Hooks).
                Default: False
            **kwargs: Reserved for future use

        Returns:
            If as_dict=False: Dict[str, Bundle] - validated Pydantic Bundle objects grouped by resource type
                Example: {"observation": Bundle(...), "patient": Bundle(...)}
            If as_dict=True: Dict[str, Any] - single combined bundle dict (no validation)
                Example: {"type": "collection", "entry": [...]}

        Raises:
            FileNotFoundError: If directory or resource files not found
            ValueError: If resource_types is None/empty or resources fail validation

        Examples:
            CDS Hooks prefetch format (validated, grouped by resource type):
            >>> loader = MimicOnFHIRLoader()
            >>> prefetch = loader.load(
            ...     data_dir="./data/mimic-iv-fhir",
            ...     resource_types=["MimicMedication", "MimicCondition"]
            ... )
            >>> prefetch["medicationstatement"]  # Pydantic Bundle object

            ML workflow (single bundle dict, fast, no validation):
            >>> bundle = loader.load(
            ...     data_dir="./data/mimic-iv-fhir",
            ...     resource_types=["MimicObservationChartevents", "MimicPatient"],
            ...     as_dict=True
            ... )
            >>> from healthchain.io import Dataset
            >>> dataset = Dataset.from_fhir_bundle(bundle, schema="sepsis_vitals.yaml")
        """

        data_dir = Path(data_dir)
        if not data_dir.exists():
            raise FileNotFoundError(
                f"MIMIC-on-FHIR data directory not found at: {data_dir}\n"
                f"Please ensure the directory exists and contains a 'fhir' subdirectory with .ndjson.gz files.\n"
                f"Expected structure: {data_dir}/fhir/MimicMedication.ndjson.gz, etc."
            )

        # Check if /fhir subdirectory exists
        fhir_dir = data_dir / "fhir"
        if not fhir_dir.exists():
            raise FileNotFoundError(
                f"MIMIC-on-FHIR 'fhir' subdirectory not found at: {fhir_dir}\n"
                f"The loader expects data_dir to contain a 'fhir' subdirectory with .ndjson.gz resource files.\n"
                f"Expected structure:\n"
                f"  {data_dir}/\n"
                f"  └── fhir/\n"
                f"      ├── MimicMedication.ndjson.gz\n"
                f"      ├── MimicCondition.ndjson.gz\n"
                f"      └── ... (other resource files)"
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
                    data_dir, resource_type, sample_size
                )

                # Group by FHIR resourceType (not filename)
                for resource in resources:
                    fhir_type = resource.get("resourceType")
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

        # ML workflow
        if as_dict:
            all_entries = []
            for resources in resources_by_type.values():
                all_entries.extend([{"resource": r} for r in resources])

            return {"type": "collection", "entry": all_entries}

        # CDS Hooks prefetch
        bundles = {}
        for fhir_type, resources in resources_by_type.items():
            bundles[fhir_type.lower()] = Bundle(
                type="collection",
                entry=[{"resource": resource} for resource in resources],
            )

        return bundles

    def _load_resource_file(
        self, data_dir: Path, resource_type: str, sample_size: Optional[int] = None
    ) -> List[Dict]:
        """
        Load resources from a single MIMIC-on-FHIR .ndjson.gz file.

        Args:
            data_dir: Path to MIMIC-on-FHIR data directory
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

        # Construct file path - MIMIC-on-FHIR stores resources in /fhir subdirectory
        fhir_dir = data_dir / "fhir"
        file_path = fhir_dir / f"{resource_type}.ndjson.gz"

        if not file_path.exists():
            # Provide helpful error with available files
            available_files = []
            if fhir_dir.exists():
                available_files = [f.stem for f in fhir_dir.glob("*.ndjson.gz")]

            error_msg = f"Resource file not found: {file_path}\n"
            error_msg += (
                f"Expected MIMIC-on-FHIR file at {fhir_dir}/{resource_type}.ndjson.gz\n"
            )

            if available_files:
                error_msg += f"\nAvailable resource files in {fhir_dir}:\n"
                error_msg += "\n".join(f"  - {f}" for f in available_files[:10])
                if len(available_files) > 10:
                    error_msg += f"\n  ... and {len(available_files) - 10} more"
            else:
                error_msg += f"\nNo .ndjson.gz files found in {fhir_dir}"

            raise FileNotFoundError(error_msg)

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
