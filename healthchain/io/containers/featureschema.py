"""Feature schema definitions for FHIR to Dataset data conversion.

This module provides classes to define and manage feature schemas that map
FHIR resources to pandas DataFrame columns for ML model deployment.
"""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Any


@dataclass
class FeatureMapping:
    """Maps a single feature to its FHIR source."""

    name: str
    fhir_resource: str
    code: Optional[str] = None
    code_system: Optional[str] = None
    field: Optional[str] = None
    transform: Optional[str] = None
    dtype: str = "float64"
    required: bool = True
    unit: Optional[str] = None
    display: Optional[str] = None

    def __post_init__(self):
        """Validate the feature mapping configuration."""
        if self.fhir_resource == "Observation":
            if not self.code:
                raise ValueError(
                    f"Feature '{self.name}': Observation resources require a 'code'"
                )
            if not self.code_system:
                raise ValueError(
                    f"Feature '{self.name}': Observation resources require a 'code_system'"
                )
        elif self.fhir_resource == "Patient":
            if not self.field:
                raise ValueError(
                    f"Feature '{self.name}': Patient resources require a 'field'"
                )

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "FeatureMapping":
        """Create a FeatureMapping from a dictionary.

        Args:
            name: The feature name
            data: Dictionary containing feature configuration

        Returns:
            FeatureMapping instance
        """
        return cls(name=name, **data)


@dataclass
class FeatureSchema:
    """Schema defining how to extract features from FHIR resources."""

    name: str
    version: str
    features: Dict[str, FeatureMapping] = field(default_factory=dict)
    description: Optional[str] = None
    model_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Convert feature dicts to FeatureMapping objects if needed."""
        if self.features and isinstance(list(self.features.values())[0], dict):
            self.features = {
                name: FeatureMapping.from_dict(name, mapping)
                for name, mapping in self.features.items()
            }

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "FeatureSchema":
        """Load schema from a YAML file.

        Args:
            path: Path to the YAML file

        Returns:
            FeatureSchema instance

        Example:
            >>> schema = FeatureSchema.from_yaml("configs/features/sepsis_vitals.yaml")
        """
        path = Path(path)
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureSchema":
        """Create a FeatureSchema from a dictionary.

        Args:
            data: Dictionary containing schema configuration

        Returns:
            FeatureSchema instance
        """
        # Convert feature dicts to FeatureMapping objects
        features_data = data.get("features", {})
        features = {
            name: FeatureMapping.from_dict(name, mapping)
            for name, mapping in features_data.items()
        }

        return cls(
            name=data["name"],
            version=data["version"],
            features=features,
            description=data.get("description"),
            model_info=data.get("model_info"),
            metadata=data.get("metadata"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary format.

        Returns:
            Dictionary representation of the schema
        """
        result = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "model_info": self.model_info,
            "features": {
                name: {
                    k: v
                    for k, v in vars(mapping).items()
                    if k != "name" and v is not None
                }
                for name, mapping in self.features.items()
            },
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def to_yaml(self, path: Union[str, Path]) -> None:
        """Save schema to a YAML file.

        Args:
            path: Path where the YAML file will be saved
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    def get_feature_names(self) -> List[str]:
        """Get list of feature names in order.

        Returns:
            List of feature names
        """
        return list(self.features.keys())

    def get_required_features(self) -> List[str]:
        """Get list of required feature names.

        Returns:
            List of required feature names
        """
        return [name for name, mapping in self.features.items() if mapping.required]

    def get_features_by_resource(self, resource_type: str) -> Dict[str, FeatureMapping]:
        """Get all features mapped to a specific FHIR resource type.

        Args:
            resource_type: FHIR resource type (e.g., "Observation", "Patient")

        Returns:
            Dictionary of features for the specified resource type
        """
        return {
            name: mapping
            for name, mapping in self.features.items()
            if mapping.fhir_resource == resource_type
        }

    def get_observation_codes(self) -> Dict[str, FeatureMapping]:
        """Get all Observation features with their codes.

        Returns:
            Dictionary mapping codes to feature mappings
        """
        observations = self.get_features_by_resource("Observation")
        return {
            mapping.code: mapping for mapping in observations.values() if mapping.code
        }

    def validate_dataframe_columns(self, columns: List[str]) -> Dict[str, Any]:
        """Validate that a DataFrame has the expected columns.

        Args:
            columns: List of column names from a DataFrame

        Returns:
            Dictionary with validation results:
                - valid: bool
                - missing_required: List of missing required features
                - unexpected: List of unexpected columns
        """
        expected = set(self.get_feature_names())
        actual = set(columns)
        required = set(self.get_required_features())

        missing_required = list(required - actual)
        unexpected = list(actual - expected)

        return {
            "valid": len(missing_required) == 0,
            "missing_required": missing_required,
            "unexpected": unexpected,
            "missing_optional": list((expected - required) - actual),
        }
