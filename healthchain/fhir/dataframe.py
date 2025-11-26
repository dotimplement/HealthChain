"""FHIR to DataFrame converters.

This module provides generic functions to convert FHIR Bundles to pandas DataFrames
for analysis and ML model deployment.

In instances where there are multiple codes present for a single resource, the first code is used as the primary code.
"""

import pandas as pd
import logging

from typing import Any, Dict, List, Union, Optional, Literal
from collections import defaultdict
from fhir.resources.bundle import Bundle
from pydantic import BaseModel, field_validator, ConfigDict

from healthchain.fhir.utilities import (
    calculate_age_from_birthdate,
    calculate_age_from_event_date,
    encode_gender,
)

logger = logging.getLogger(__name__)


# Resource handler registry
SUPPORTED_RESOURCES = {
    "Patient": {
        "handler": "_flatten_patient",
        "description": "Patient demographics (age, gender)",
        "output_columns": ["age", "gender"],
    },
    "Observation": {
        "handler": "_flatten_observations",
        "description": "Clinical observations (vitals, labs)",
        "output_columns": "Dynamic based on observation codes",
        "options": ["aggregation"],
    },
    "Condition": {
        "handler": "_flatten_conditions",
        "description": "Conditions/diagnoses as binary indicators",
        "output_columns": "Dynamic: condition_{code}_{display}",
    },
    "MedicationStatement": {
        "handler": "_flatten_medications",
        "description": "Medications as binary indicators",
        "output_columns": "Dynamic: medication_{code}_{display}",
    },
}


class BundleConverterConfig(BaseModel):
    """Configuration for FHIR Bundle to DataFrame conversion.

    This configuration object controls which FHIR resources are processed and how
    they are converted to DataFrame columns for ML model deployment.

    Attributes:
        resources: List of FHIR resource types to include in the conversion
        observation_aggregation: How to aggregate multiple observation values
        age_calculation: Method for calculating patient age
        event_date_source: Which resource to extract event date from
        event_date_strategy: Which date to use when multiple dates exist
        resource_options: Resource-specific configuration options (extensible)

    Example:
        >>> config = BundleConverterConfig(
        ...     resources=["Patient", "Observation", "Condition"],
        ...     observation_aggregation="median"
        ... )
        >>> df = bundle_to_dataframe(bundle, config=config)
    """

    # Core resources to include
    resources: List[str] = ["Patient", "Observation"]

    # Observation-specific options
    observation_aggregation: Literal["mean", "median", "max", "min", "last"] = "mean"

    # Patient age calculation
    age_calculation: Literal["current_date", "event_date"] = "current_date"
    event_date_source: Literal["Observation", "Encounter"] = "Observation"
    event_date_strategy: Literal["earliest", "latest", "first"] = "earliest"

    # Resource-specific options (extensible for future use)
    resource_options: Dict[str, Dict[str, Any]] = {}

    model_config = ConfigDict(extra="allow")

    @field_validator("resources")
    @classmethod
    def validate_resources(cls, v):
        """Validate that requested resources are supported and warn about unsupported ones."""
        supported = get_supported_resources()
        unsupported = [r for r in v if r not in supported]
        if unsupported:
            logger.warning(
                f"Unsupported resources will be skipped: {unsupported}. "
                f"Supported resources: {supported}"
            )
        return v


def get_supported_resources() -> List[str]:
    """Get list of supported FHIR resource types.

    Returns:
        List of resource type names that can be converted to DataFrame columns

    Example:
        >>> resources = get_supported_resources()
        >>> print(resources)
        ['Patient', 'Observation', 'Condition', 'MedicationStatement']
    """
    return list(SUPPORTED_RESOURCES.keys())


def get_resource_info(resource_type: str) -> Dict[str, Any]:
    """Get detailed information about a supported resource type.

    Args:
        resource_type: FHIR resource type name

    Returns:
        Dictionary with resource handler information, or empty dict if unsupported

    Example:
        >>> info = get_resource_info("Observation")
        >>> print(info["description"])
        'Clinical observations (vitals, labs)'
    """
    return SUPPORTED_RESOURCES.get(resource_type, {})


def print_supported_resources() -> None:
    """Print user-friendly list of supported FHIR resources for conversion.

    Example:
        >>> from healthchain.fhir.converters import print_supported_resources
        >>> print_supported_resources()
        Supported FHIR Resources for ML Dataset Conversion:

          ✓ Patient
            Patient demographics (age, gender)
            Columns: age, gender
        ...
    """
    print("Supported FHIR Resources for ML Dataset Conversion:\n")
    for resource, info in SUPPORTED_RESOURCES.items():
        print(f"  ✓ {resource}")
        print(f"    {info['description']}")
        if isinstance(info["output_columns"], list):
            print(f"    Columns: {', '.join(info['output_columns'])}")
        else:
            print(f"    Columns: {info['output_columns']}")
        if info.get("options"):
            print(f"    Options: {', '.join(info['options'])}")
        print()


def _get_field(resource: Dict, field_name: str, default=None):
    """Get field value from a dictionary."""
    return resource.get(field_name, default)


def _get_reference(field: Union[str, Dict[str, Any]]) -> Optional[str]:
    """Extract reference string from a FHIR Reference field."""

    if not field:
        return None

    # Case 1: Already a string
    if isinstance(field, str):
        return field

    # Case 2: Dict with 'reference' field
    return _get_field(field, "reference")


def extract_observation_value(observation: Dict) -> Optional[float]:
    """Extract numeric value from an Observation dict.

    Handles different value types (valueQuantity, valueInteger, valueString) and
    attempts to convert to float.
    """

    try:
        value_quantity = _get_field(observation, "valueQuantity")
        if value_quantity:
            value = _get_field(value_quantity, "value")
            if value is not None:
                return float(value)

        value_int = _get_field(observation, "valueInteger")
        if value_int is not None:
            return float(value_int)

        value_str = _get_field(observation, "valueString")
        if value_str:
            return float(value_str)

    except (ValueError, TypeError):
        pass

    return None


def extract_event_date(
    resources: Dict[str, List[Any]],
    source: str = "Observation",
    strategy: str = "earliest",
) -> Optional[str]:
    """Extract event date from patient resources for age calculation.

    Used primarily for MIMIC-IV on FHIR datasets where age is calculated
    based on event dates rather than current date.

    Args:
        resources: Dictionary of patient resources (from group_bundle_by_patient)
        source: Which resource type to extract date from ("Observation" or "Encounter")
        strategy: Which date to use ("earliest", "latest", "first")

    Returns:
        Event date in ISO format, or None if no suitable date found

    Example:
        >>> resources = {"observations": [obs1, obs2], "encounters": [enc1]}
        >>> event_date = extract_event_date(resources, source="Observation", strategy="earliest")
    """
    if source == "Observation":
        items = resources.get("observations", [])
        date_field = "effectiveDateTime"
    elif source == "Encounter":
        items = resources.get("encounters", [])
        date_field = "period"
    else:
        return None

    if not items:
        return None

    dates = []
    for item in items:
        if source == "Encounter":
            # Extract start date from period
            period = _get_field(item, date_field)
            if period:
                start = _get_field(period, "start")
                if start:
                    dates.append(start)
        else:
            # Direct date field
            date_value = _get_field(item, date_field)
            if date_value:
                dates.append(date_value)

    if not dates:
        return None

    # Apply strategy
    if strategy == "earliest":
        return min(dates)
    elif strategy == "latest":
        return max(dates)
    elif strategy == "first":
        return dates[0]
    else:
        return min(dates)  # Default to earliest


def group_bundle_by_patient(
    bundle: Union[Bundle, Dict[str, Any]],
) -> Dict[str, Dict[str, List[Any]]]:
    """Group Bundle resources by patient reference.

    Organizes FHIR resources in a Bundle by their associated patient, making it easier
    to process patient-centric data. Accepts both Pydantic Bundle objects and dicts,
    converts to dict internally for performance.

    Args:
        bundle: FHIR Bundle resource (Pydantic object or dict)

    Returns:
        Dictionary mapping patient references to their resources:
        {
            "Patient/123": {
                "patient": Patient resource dict,
                "observations": [Observation dict, ...],
                "conditions": [Condition dict, ...],
                ...
            }
        }
    """
    if not isinstance(bundle, dict):
        bundle = bundle.model_dump()

    patient_data = defaultdict(
        lambda: {
            "patient": None,
            "observations": [],
            "conditions": [],
            "medications": [],
            "allergies": [],
            "procedures": [],
            "encounters": [],
            "other": [],
        }
    )

    # Get bundle entries
    entries = _get_field(bundle, "entry")
    if not entries:
        return dict(patient_data)

    for entry in entries:
        # Get resource from entry
        resource = _get_field(entry, "resource")
        if not resource:
            continue

        resource_type = _get_field(resource, "resourceType")
        resource_id = _get_field(resource, "id")

        if resource_type == "Patient":
            patient_ref = f"Patient/{resource_id}"
            patient_data[patient_ref]["patient"] = resource

        else:
            # Get patient reference from resource
            subject = _get_field(resource, "subject")
            patient_field = _get_field(resource, "patient")

            patient_ref = _get_reference(subject) or _get_reference(patient_field)

            if patient_ref:
                # Add to appropriate list based on resource type
                if resource_type == "Observation":
                    patient_data[patient_ref]["observations"].append(resource)
                elif resource_type == "Condition":
                    patient_data[patient_ref]["conditions"].append(resource)
                elif resource_type == "MedicationStatement":
                    patient_data[patient_ref]["medications"].append(resource)
                elif resource_type == "AllergyIntolerance":
                    patient_data[patient_ref]["allergies"].append(resource)
                elif resource_type == "Procedure":
                    patient_data[patient_ref]["procedures"].append(resource)
                elif resource_type == "Encounter":
                    patient_data[patient_ref]["encounters"].append(resource)
                else:
                    patient_data[patient_ref]["other"].append(resource)

    return dict(patient_data)


def bundle_to_dataframe(
    bundle: Union[Bundle, Dict[str, Any]],
    config: Optional[BundleConverterConfig] = None,
) -> pd.DataFrame:
    """Convert a FHIR Bundle to a pandas DataFrame.

    Converts FHIR resources to a tabular format with one row per patient.
    Uses a configuration object to control which resources are processed and how.

    Args:
        bundle: FHIR Bundle resource (object or dict)
        config: BundleConverterConfig object specifying conversion behavior.
            If None, uses default config (Patient + Observation with mean aggregation)

    Returns:
        DataFrame with one row per patient and columns for each feature

    Example:
        >>> from healthchain.fhir.converters import BundleConverterConfig
        >>>
        >>> # Default behavior
        >>> df = bundle_to_dataframe(bundle)
        >>>
        >>> # Custom config
        >>> config = BundleConverterConfig(
        ...     resources=["Patient", "Observation", "Condition"],
        ...     observation_aggregation="median",
        ...     age_calculation="event_date"
        ... )
        >>> df = bundle_to_dataframe(bundle, config=config)
    """
    # Use default config if not provided
    if config is None:
        config = BundleConverterConfig()

    # Group resources by patient
    patient_data = group_bundle_by_patient(bundle)

    if not patient_data:
        return pd.DataFrame()

    # Build rows for each patient
    rows = []
    for patient_ref, resources in patient_data.items():
        row = {"patient_ref": patient_ref}

        # Process each requested resource type using registry
        for resource_type in config.resources:
            handler_info = SUPPORTED_RESOURCES.get(resource_type)

            if not handler_info:
                # Skip unsupported resources gracefully (already warned by validator)
                continue

            # Get handler function by name
            handler_name = handler_info["handler"]
            handler = globals()[handler_name]

            # Call handler with standardized signature
            features = handler(resources, config)
            if features:
                row.update(features)

        rows.append(row)

    return pd.DataFrame(rows)


def _flatten_patient(
    resources: Dict[str, Any], config: BundleConverterConfig
) -> Dict[str, Any]:
    """Flatten patient demographics into feature columns.

    Args:
        resources: Dictionary of patient resources
        config: Converter configuration

    Returns:
        Dictionary with age and gender features
    """
    if not resources["patient"]:
        return {}

    features = {}
    patient = resources["patient"]

    birth_date = _get_field(patient, "birthDate")
    gender = _get_field(patient, "gender")

    # Calculate age based on configuration
    if config.age_calculation == "event_date":
        event_date = extract_event_date(
            resources, config.event_date_source, config.event_date_strategy
        )
        features["age"] = calculate_age_from_event_date(birth_date, event_date)
    else:
        features["age"] = calculate_age_from_birthdate(birth_date)

    features["gender"] = encode_gender(gender)

    return features


def _flatten_observations(
    resources: Dict[str, Any], config: BundleConverterConfig
) -> Dict[str, float]:
    """Flatten observations into feature columns.

    Args:
        resources: Dictionary of patient resources
        config: Converter configuration

    Returns:
        Dictionary with observation features
    """
    observations = resources.get("observations", [])
    aggregation = config.observation_aggregation
    import numpy as np

    # Group observations by code
    obs_by_code = defaultdict(list)

    for obs in observations:
        code_field = _get_field(obs, "code")
        if not code_field:
            continue

        coding_array = _get_field(code_field, "coding")
        if not coding_array or len(coding_array) == 0:
            continue

        coding = coding_array[0]
        code = _get_field(coding, "code")
        display = _get_field(coding, "display") or code
        system = _get_field(coding, "system")

        value = extract_observation_value(obs)
        if value is not None:
            obs_by_code[code].append(
                {
                    "value": value,
                    "display": display,
                    "system": system,
                }
            )

    # Aggregate and create feature columns
    features = {}
    for code, obs_list in obs_by_code.items():
        values = [item["value"] for item in obs_list]
        display = obs_list[0]["display"]

        # Create column name: code_display
        col_name = f"{code}_{display.replace(' ', '_')}"

        # Aggregate values
        if aggregation == "mean":
            features[col_name] = np.mean(values)
        elif aggregation == "median":
            features[col_name] = np.median(values)
        elif aggregation == "max":
            features[col_name] = np.max(values)
        elif aggregation == "min":
            features[col_name] = np.min(values)
        elif aggregation == "last":
            features[col_name] = values[-1]
        else:
            features[col_name] = np.mean(values)

    return features


def _flatten_conditions(
    resources: Dict[str, Any], config: BundleConverterConfig
) -> Dict[str, int]:
    """Flatten conditions into binary indicator columns.

    Args:
        resources: Dictionary of patient resources
        config: Converter configuration

    Returns:
        Dictionary with condition indicator features
    """
    conditions = resources.get("conditions", [])
    features = {}

    for condition in conditions:
        code_field = _get_field(condition, "code")
        if not code_field:
            continue

        coding_array = _get_field(code_field, "coding")
        if not coding_array or len(coding_array) == 0:
            continue

        # Get primary coding
        coding = coding_array[0]
        code = _get_field(coding, "code")
        display = _get_field(coding, "display") or code

        # Create column name: condition_code_display
        col_name = f"condition_{code}_{display.replace(' ', '_')}"
        features[col_name] = 1

    return features


def _flatten_medications(
    resources: Dict[str, Any], config: BundleConverterConfig
) -> Dict[str, int]:
    """Flatten medications into binary indicator columns.

    Args:
        resources: Dictionary of patient resources
        config: Converter configuration

    Returns:
        Dictionary with medication indicator features
    """
    medications = resources.get("medications", [])
    features = {}

    for med in medications:
        medication = _get_field(med, "medication")
        if not medication:
            continue

        med_concept = _get_field(medication, "concept")
        if not med_concept:
            continue

        coding_array = _get_field(med_concept, "coding")
        if not coding_array or len(coding_array) == 0:
            continue

        # Get primary coding
        coding = coding_array[0]
        code = _get_field(coding, "code")
        display = _get_field(coding, "display") or code

        # Create column name: medication_code_display
        col_name = f"medication_{code}_{display.replace(' ', '_')}"
        features[col_name] = 1

    return features
