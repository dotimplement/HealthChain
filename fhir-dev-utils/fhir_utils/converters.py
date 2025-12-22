"""
FHIR Format Converters

Provides utilities for converting FHIR resources to and from
various formats including dictionaries, DataFrames, and flat structures.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union, Type
from collections import defaultdict

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.medicationstatement import MedicationStatement


class FHIRConverter:
    """
    Comprehensive FHIR format converter.

    Provides methods for converting FHIR resources to and from
    various formats for analysis and integration purposes.
    """

    @staticmethod
    def resource_to_dict(
        resource: Resource,
        exclude_none: bool = True,
        exclude_meta: bool = False
    ) -> Dict[str, Any]:
        """
        Convert a FHIR resource to a dictionary.

        Args:
            resource: FHIR resource
            exclude_none: Remove None values
            exclude_meta: Remove meta field

        Returns:
            Dictionary representation
        """
        data = resource.model_dump(exclude_none=exclude_none)
        if exclude_meta and "meta" in data:
            del data["meta"]
        return data

    @staticmethod
    def dict_to_resource(
        data: Dict[str, Any],
        resource_type: Optional[Type[Resource]] = None
    ) -> Resource:
        """
        Convert a dictionary to a FHIR resource.

        Args:
            data: Dictionary with FHIR data
            resource_type: Optional explicit resource type

        Returns:
            FHIR resource
        """
        if resource_type:
            return resource_type(**data)

        # Auto-detect resource type
        type_name = data.get("resourceType")
        if not type_name:
            raise ValueError("Dictionary must have 'resourceType' field")

        from fhir.resources import get_fhir_model_class
        model_class = get_fhir_model_class(type_name)
        return model_class(**data)

    @staticmethod
    def bundle_to_resource_list(
        bundle: Union[Bundle, Dict[str, Any]]
    ) -> List[Resource]:
        """
        Extract all resources from a bundle into a flat list.

        Args:
            bundle: FHIR bundle

        Returns:
            List of resources
        """
        if isinstance(bundle, dict):
            bundle = Bundle(**bundle)

        resources = []
        for entry in bundle.entry or []:
            if entry.resource:
                resources.append(entry.resource)
        return resources

    @staticmethod
    def flatten_resource(
        resource: Union[Resource, Dict[str, Any]],
        prefix: str = "",
        separator: str = "_",
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Flatten a nested FHIR resource to a single-level dictionary.

        Args:
            resource: FHIR resource
            prefix: Key prefix
            separator: Separator for nested keys
            max_depth: Maximum nesting depth

        Returns:
            Flattened dictionary
        """
        if isinstance(resource, Resource):
            data = resource.model_dump(exclude_none=True)
        else:
            data = resource

        result = {}

        def _flatten(obj: Any, key: str, depth: int) -> None:
            if depth > max_depth:
                result[key] = str(obj)
                return

            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_key = f"{key}{separator}{k}" if key else k
                    _flatten(v, new_key, depth + 1)
            elif isinstance(obj, list):
                if len(obj) == 1:
                    _flatten(obj[0], key, depth)
                else:
                    for i, item in enumerate(obj):
                        _flatten(item, f"{key}{separator}{i}", depth + 1)
            else:
                result[key] = obj

        _flatten(data, prefix, 0)
        return result


def bundle_to_flat_dict(
    bundle: Union[Bundle, Dict[str, Any]],
    include_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Convert a bundle to a list of flattened dictionaries.

    Args:
        bundle: FHIR bundle
        include_types: Optional list of resource types to include

    Returns:
        List of flattened dictionaries
    """
    converter = FHIRConverter()

    if isinstance(bundle, dict):
        bundle = Bundle(**bundle)

    result = []
    for entry in bundle.entry or []:
        if not entry.resource:
            continue

        res_type = entry.resource.resource_type
        if include_types and res_type not in include_types:
            continue

        flat = converter.flatten_resource(entry.resource)
        flat["_resource_type"] = res_type
        result.append(flat)

    return result


def dict_to_resource(
    data: Dict[str, Any],
    resource_type: Optional[Type[Resource]] = None
) -> Resource:
    """
    Convert a dictionary to a FHIR resource.

    Args:
        data: Dictionary with FHIR data
        resource_type: Optional explicit resource type

    Returns:
        FHIR resource
    """
    return FHIRConverter.dict_to_resource(data, resource_type)


def resources_to_dataframe(
    resources: List[Union[Resource, Dict[str, Any]]],
    resource_type: Optional[str] = None,
    columns: Optional[List[str]] = None,
    flatten: bool = True
) -> "pd.DataFrame":
    """
    Convert a list of FHIR resources to a pandas DataFrame.

    Args:
        resources: List of FHIR resources
        resource_type: Filter to specific resource type
        columns: Specific columns to include
        flatten: Whether to flatten nested structures

    Returns:
        pandas DataFrame

    Raises:
        ImportError: If pandas is not installed
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required for DataFrame operations")

    converter = FHIRConverter()
    rows = []

    for resource in resources:
        if isinstance(resource, dict):
            res_type = resource.get("resourceType")
            data = resource
        else:
            res_type = resource.resource_type
            data = resource.model_dump(exclude_none=True)

        if resource_type and res_type != resource_type:
            continue

        if flatten:
            row = converter.flatten_resource(data)
        else:
            row = data

        rows.append(row)

    df = pd.DataFrame(rows)

    if columns:
        available = [c for c in columns if c in df.columns]
        df = df[available]

    return df


def dataframe_to_resources(
    df: "pd.DataFrame",
    resource_type: Type[Resource],
    column_mapping: Optional[Dict[str, str]] = None
) -> List[Resource]:
    """
    Convert a pandas DataFrame to FHIR resources.

    Args:
        df: pandas DataFrame
        resource_type: Target FHIR resource type
        column_mapping: Optional mapping of DataFrame columns to FHIR fields

    Returns:
        List of FHIR resources
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required for DataFrame operations")

    resources = []

    for _, row in df.iterrows():
        data = row.to_dict()

        # Apply column mapping
        if column_mapping:
            mapped_data = {}
            for df_col, fhir_field in column_mapping.items():
                if df_col in data:
                    mapped_data[fhir_field] = data[df_col]
            data = mapped_data

        # Remove NaN values
        data = {k: v for k, v in data.items() if pd.notna(v)}

        # Add resource type
        data["resourceType"] = resource_type.__name__

        try:
            resource = resource_type(**data)
            resources.append(resource)
        except Exception:
            # Skip invalid rows
            continue

    return resources


class PatientDataExtractor:
    """
    Specialized extractor for patient-centric data from bundles.

    Useful for ML workflows that need patient-level features.
    """

    def __init__(self, bundle: Union[Bundle, Dict[str, Any]]):
        """Initialize with a bundle."""
        if isinstance(bundle, dict):
            self._bundle = Bundle(**bundle)
        else:
            self._bundle = bundle

        self._patient_data: Dict[str, Dict[str, Any]] = {}
        self._build_patient_data()

    def _build_patient_data(self) -> None:
        """Build patient-centric data structure."""
        # First pass: index patients
        for entry in self._bundle.entry or []:
            resource = entry.resource
            if resource and resource.resource_type == "Patient":
                patient_id = getattr(resource, "id", None)
                if patient_id:
                    self._patient_data[patient_id] = {
                        "patient": resource,
                        "conditions": [],
                        "observations": [],
                        "medications": [],
                        "allergies": [],
                    }

        # Second pass: associate resources with patients
        for entry in self._bundle.entry or []:
            resource = entry.resource
            if not resource:
                continue

            patient_ref = self._get_patient_ref(resource)
            if not patient_ref:
                continue

            # Extract patient ID from reference
            patient_id = patient_ref.split("/")[-1]
            if patient_id not in self._patient_data:
                continue

            res_type = resource.resource_type
            if res_type == "Condition":
                self._patient_data[patient_id]["conditions"].append(resource)
            elif res_type == "Observation":
                self._patient_data[patient_id]["observations"].append(resource)
            elif res_type == "MedicationStatement":
                self._patient_data[patient_id]["medications"].append(resource)
            elif res_type == "AllergyIntolerance":
                self._patient_data[patient_id]["allergies"].append(resource)

    def _get_patient_ref(self, resource: Resource) -> Optional[str]:
        """Get patient reference from resource."""
        for field in ["subject", "patient"]:
            ref = getattr(resource, field, None)
            if ref and hasattr(ref, "reference"):
                return ref.reference
        return None

    def get_patient_ids(self) -> List[str]:
        """Get all patient IDs in the bundle."""
        return list(self._patient_data.keys())

    def get_patient_data(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get all data for a specific patient."""
        return self._patient_data.get(patient_id)

    def to_feature_dict(
        self,
        patient_id: str,
        include_demographics: bool = True,
        aggregate_observations: bool = True,
        count_conditions: bool = True
    ) -> Dict[str, Any]:
        """
        Convert patient data to a feature dictionary for ML.

        Args:
            patient_id: Patient ID
            include_demographics: Include age, gender
            aggregate_observations: Include latest vitals
            count_conditions: Include condition counts

        Returns:
            Feature dictionary
        """
        data = self._patient_data.get(patient_id)
        if not data:
            return {}

        features: Dict[str, Any] = {"patient_id": patient_id}
        patient = data["patient"]

        # Demographics
        if include_demographics:
            features["gender"] = getattr(patient, "gender", None)

            birth_date = getattr(patient, "birthDate", None)
            if birth_date:
                if isinstance(birth_date, str):
                    birth_date = datetime.fromisoformat(birth_date.replace("Z", "+00:00"))
                today = datetime.now()
                age = (today - datetime(birth_date.year, birth_date.month, birth_date.day)).days // 365
                features["age"] = age

        # Condition counts
        if count_conditions:
            features["condition_count"] = len(data["conditions"])
            features["medication_count"] = len(data["medications"])
            features["allergy_count"] = len(data["allergies"])

        # Latest observations
        if aggregate_observations:
            obs_by_code: Dict[str, Any] = {}
            for obs in data["observations"]:
                code = self._get_observation_code(obs)
                if code:
                    value = self._get_observation_value(obs)
                    effective = getattr(obs, "effectiveDateTime", None)

                    # Keep latest observation per code
                    if code not in obs_by_code or (effective and effective > obs_by_code[code].get("effective")):
                        obs_by_code[code] = {"value": value, "effective": effective}

            for code, data in obs_by_code.items():
                features[f"obs_{code}"] = data["value"]

        return features

    def _get_observation_code(self, obs: Observation) -> Optional[str]:
        """Extract observation code."""
        code = getattr(obs, "code", None)
        if code and code.coding:
            return code.coding[0].code
        return None

    def _get_observation_value(self, obs: Observation) -> Any:
        """Extract observation value."""
        if hasattr(obs, "valueQuantity") and obs.valueQuantity:
            return obs.valueQuantity.value
        if hasattr(obs, "valueString") and obs.valueString:
            return obs.valueString
        if hasattr(obs, "valueCodeableConcept") and obs.valueCodeableConcept:
            if obs.valueCodeableConcept.coding:
                return obs.valueCodeableConcept.coding[0].code
        return None

    def to_dataframe(self) -> "pd.DataFrame":
        """
        Convert all patients to a feature DataFrame.

        Returns:
            pandas DataFrame with one row per patient
        """
        if not HAS_PANDAS:
            raise ImportError("pandas is required for DataFrame operations")

        rows = []
        for patient_id in self.get_patient_ids():
            features = self.to_feature_dict(patient_id)
            rows.append(features)

        return pd.DataFrame(rows)
