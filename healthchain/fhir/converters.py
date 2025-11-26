"""FHIR to DataFrame converters.

This module provides generic functions to convert FHIR Bundles to pandas DataFrames
for analysis and ML model deployment.

In instances where there are multiple codes present for a single resource, the first code is used as the primary code.
"""

import pandas as pd

from typing import Any, Dict, List, Union, Optional
from collections import defaultdict
from fhir.resources.bundle import Bundle

from healthchain.fhir.helpers import (
    calculate_age_from_birthdate,
    calculate_age_from_event_date,
    encode_gender,
)


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
    include_patient: bool = True,
    include_observations: bool = True,
    include_conditions: bool = False,
    include_medications: bool = False,
    observation_aggregation: str = "mean",
    use_event_date_for_age: bool = False,
    event_date_source: str = "Observation",
    event_date_strategy: str = "earliest",
) -> pd.DataFrame:
    """Convert a FHIR Bundle to a pandas DataFrame.

    Generic flattener that converts FHIR resources to Dataset format with one row per patient.
    Observations are aggregated by code, and patient demographics are included.
    Works with both FHIR objects and raw dictionaries.

    Args:
        bundle: FHIR Bundle resource (object or dict)
        include_patient: Include patient demographics (age, gender) (default: True)
        include_observations: Include observations as columns (default: True)
        include_conditions: Include condition codes as columns (default: False)
        include_medications: Include medication codes as columns (default: False)
        observation_aggregation: How to aggregate multiple observation values
            Options: "mean", "median", "max", "min", "last" (default: "mean")
        use_event_date_for_age: Use event date for age calculation (MIMIC-IV style) (default: False)
        event_date_source: Which resource to extract event date from ("Observation" or "Encounter") (default: "Observation")
        event_date_strategy: Which date to use ("earliest", "latest", "first") (default: "earliest")

    Returns:
        DataFrame with one row per patient and columns for each feature

    Example:
        >>> from fhir.resources.bundle import Bundle
        >>> bundle = Bundle(**patient_data)
        >>> df = bundle_to_dataframe(bundle)
        >>> print(df.columns)
        Index(['patient_ref', 'age', 'gender', '8867-4_Heart_rate', ...], dtype='object')

        >>> # MIMIC-IV style age calculation
        >>> df = bundle_to_dataframe(bundle, use_event_date_for_age=True)
    """
    # Group resources by patient
    patient_data = group_bundle_by_patient(bundle)

    if not patient_data:
        return pd.DataFrame()

    # Build rows for each patient
    rows = []
    for patient_ref, resources in patient_data.items():
        row = {"patient_ref": patient_ref}

        # Add patient demographics
        if include_patient and resources["patient"]:
            patient = resources["patient"]
            birth_date = _get_field(patient, "birthDate")
            gender = _get_field(patient, "gender")

            # Calculate age based on configuration
            if use_event_date_for_age:
                event_date = extract_event_date(
                    resources, event_date_source, event_date_strategy
                )
                row["age"] = calculate_age_from_event_date(birth_date, event_date)
            else:
                row["age"] = calculate_age_from_birthdate(birth_date)

            row["gender"] = encode_gender(gender)

        # Add observations
        if include_observations:
            obs_features = _flatten_observations(
                resources["observations"], observation_aggregation
            )
            row.update(obs_features)

        # Add conditions
        if include_conditions:
            condition_features = _flatten_conditions(resources["conditions"])
            row.update(condition_features)

        # Add medications
        if include_medications:
            med_features = _flatten_medications(resources["medications"])
            row.update(med_features)

        rows.append(row)

    return pd.DataFrame(rows)


def _flatten_observations(
    observations: List, aggregation: str = "mean"
) -> Dict[str, float]:
    """Flatten observations into feature columns."""
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


def _flatten_conditions(conditions: List) -> Dict[str, int]:
    """Flatten conditions into binary indicator columns."""

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


def _flatten_medications(medications: List) -> Dict[str, int]:
    """Flatten medications into binary indicator columns."""

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
