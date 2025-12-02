import pandas as pd
import numpy as np

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Union, Optional

from fhir.resources.bundle import Bundle
from fhir.resources.riskassessment import RiskAssessment

from healthchain.io.containers.base import DataContainer
from healthchain.io.containers.featureschema import FeatureSchema
from healthchain.io.mappers.fhirfeaturemapper import FHIRFeatureMapper
from healthchain.io.types import ValidationResult
from healthchain.fhir.resourcehelpers import (
    create_risk_assessment_from_prediction,
    create_single_codeable_concept,
)


@dataclass
class Dataset(DataContainer[pd.DataFrame]):
    """
    A container for tabular data optimized for ML inference, lightweight wrapper around a pandas DataFrame.

    Attributes:
        data: The pandas DataFrame containing the dataset.
        metadata: Dict for storing pipeline results (predictions, probabilities, etc.)

    Methods:
        from_csv: Load Dataset from CSV.
        from_dict: Load Dataset from dict.
        from_fhir_bundle: Create Dataset from FHIR Bundle and schema.
        to_csv: Save Dataset to CSV.
        to_risk_assessment: Convert predictions to FHIR RiskAssessment.
    """

    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")

    @property
    def columns(self) -> List[str]:
        return list(self.data.columns)

    @property
    def index(self) -> pd.Index:
        return self.data.index

    @property
    def dtypes(self) -> Dict[str, str]:
        return {col: str(dtype) for col, dtype in self.data.dtypes.items()}

    def column_count(self) -> int:
        return len(self.columns)

    def row_count(self) -> int:
        return len(self.data)

    def get_dtype(self, column: str) -> str:
        return str(self.data[column].dtype)

    def __iter__(self) -> Iterator[str]:
        return iter(self.columns)

    def __len__(self) -> int:
        return self.row_count()

    def describe(self) -> str:
        return f"Dataset with {self.column_count()} columns and {self.row_count()} rows"

    def remove_column(self, name: str) -> None:
        self.data.drop(columns=[name], inplace=True)

    @classmethod
    def from_csv(cls, path: str, **kwargs) -> "Dataset":
        return cls(pd.read_csv(path, **kwargs))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dataset":
        df = pd.DataFrame(data["data"])
        return cls(df)

    def to_csv(self, path: str, **kwargs) -> None:
        self.data.to_csv(path, **kwargs)

    @classmethod
    def from_fhir_bundle(
        cls,
        bundle: Union[Bundle, Dict[str, Any]],
        schema: Union[str, Path, FeatureSchema],
        aggregation: str = "mean",
    ) -> "Dataset":
        """Create Dataset from a FHIR Bundle using a feature schema.

        Extracts features from FHIR resources according to the schema specification,
        converting FHIR data to a pandas DataFrame suitable for ML inference.

        Args:
            bundle: FHIR Bundle resource (object or dict)
            schema: FeatureSchema object, or path to YAML schema file
            aggregation: How to aggregate multiple observation values (default: "mean")
                Options: "mean", "median", "max", "min", "last" (default: "mean")

        Returns:
            Dataset container with extracted features

        Example:
            >>> from fhir.resources.bundle import Bundle
            >>> bundle = Bundle(**patient_data)
            >>> dataset = Dataset.from_fhir_bundle(
            ...     bundle,
            ...     schema="healthchain/configs/features/sepsis_vitals.yaml"
            ... )
            >>> df = dataset.data
        """
        # Load schema if path provided
        if isinstance(schema, (str, Path)):
            schema = FeatureSchema.from_yaml(schema)

        # Extract features using mapper
        mapper = FHIRFeatureMapper(schema)
        df = mapper.extract_features(bundle, aggregation=aggregation)

        return cls(df)

    def validate(
        self, schema: FeatureSchema, raise_on_error: bool = False
    ) -> ValidationResult:
        """Validate DataFrame against a feature schema.

        Checks that required features are present and have correct data types.

        Args:
            schema: FeatureSchema to validate against
            raise_on_error: Whether to raise exception on validation failure

        Returns:
            ValidationResult with validation status and details

        Raises:
            ValueError: If raise_on_error is True and validation fails

        Example:
            >>> schema = FeatureSchema.from_yaml("configs/features/sepsis_vitals.yaml")
            >>> result = dataset.validate(schema)
            >>> if not result.valid:
            ...     print(result.errors)
        """
        result = ValidationResult(valid=True)

        # Check for missing required features
        required = schema.get_required_features()
        missing = [f for f in required if f not in self.data.columns]

        for feature in missing:
            result.add_missing_feature(feature)

        # Check data types for present features
        for feature_name, mapping in schema.features.items():
            if feature_name in self.data.columns:
                actual_dtype = str(self.data[feature_name].dtype)
                expected_dtype = mapping.dtype

                # Check for type mismatches (allow some flexibility)
                if not self._dtypes_compatible(actual_dtype, expected_dtype):
                    result.add_type_mismatch(feature_name, expected_dtype, actual_dtype)

        # Warn about optional missing features
        optional = set(schema.get_feature_names()) - set(required)
        missing_optional = [f for f in optional if f not in self.data.columns]

        for feature in missing_optional:
            result.add_warning(f"Optional feature '{feature}' is missing")

        if raise_on_error and not result.valid:
            raise ValueError(str(result))

        return result

    def _dtypes_compatible(self, actual: str, expected: str) -> bool:
        """Check if actual dtype is compatible with expected dtype.

        Args:
            actual: Actual dtype string
            expected: Expected dtype string

        Returns:
            True if dtypes are compatible
        """
        # Handle numeric types flexibly
        numeric_types = {"int64", "int32", "float64", "float32"}
        if expected in numeric_types and actual in numeric_types:
            return True

        # Exact match for non-numeric types
        return actual == expected

    def to_risk_assessment(
        self,
        outcome_code: str,
        outcome_display: str,
        outcome_system: str = "http://hl7.org/fhir/sid/icd-10",
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        high_threshold: float = 0.7,
        moderate_threshold: float = 0.4,
        predictions: Optional[np.ndarray] = None,
        probabilities: Optional[np.ndarray] = None,
    ) -> List[RiskAssessment]:
        """Convert model predictions to FHIR RiskAssessment resources.

        Creates RiskAssessment resources from ML model output, suitable for
        including in FHIR Bundles or sending to FHIR servers.

        Args:
            outcome_code: Code for the predicted outcome (e.g., "A41.9" for sepsis)
            outcome_display: Display text for the outcome (e.g., "Sepsis")
            outcome_system: Code system for the outcome (default: ICD-10)
            model_name: Name of the ML model (optional)
            model_version: Version of the ML model (optional)
            high_threshold: Threshold for high risk (default: 0.7)
            moderate_threshold: Threshold for moderate risk (default: 0.4)
            predictions: Binary predictions array (0/1). Defaults to metadata["predictions"]
            probabilities: Probability scores array (0-1). Defaults to metadata["probabilities"]

        Returns:
            List of RiskAssessment resources, one per patient

        Example:
            >>> risk_assessments = dataset.to_risk_assessment(
            ...     outcome_code="A41.9",
            ...     outcome_display="Sepsis, unspecified",
            ...     model_name="RandomForest",
            ...     model_version="1.0"
            ... )
        """
        # Fall back to metadata if not provided
        if predictions is None:
            predictions = self.metadata.get("predictions")
        if probabilities is None:
            probabilities = self.metadata.get("probabilities")

        if predictions is None or probabilities is None:
            raise ValueError(
                "predictions and probabilities must be provided or available in metadata"
            )

        if len(predictions) != len(self.data):
            raise ValueError(
                f"Predictions length ({len(predictions)}) must match "
                f"DataFrame length ({len(self.data)})"
            )

        if len(probabilities) != len(self.data):
            raise ValueError(
                f"Probabilities length ({len(probabilities)}) must match "
                f"DataFrame length ({len(self.data)})"
            )

        risk_assessments = []

        # Get patient references
        if "patient_ref" not in self.data.columns:
            raise ValueError("DataFrame must have 'patient_ref' column")

        for idx, row in self.data.iterrows():
            patient_ref = row["patient_ref"]
            prediction = int(predictions[idx])
            probability = float(probabilities[idx])

            # Determine qualitative risk
            if probability >= high_threshold:
                qualitative_risk = "high"
            elif probability >= moderate_threshold:
                qualitative_risk = "moderate"
            else:
                qualitative_risk = "low"

            # Build prediction dict
            prediction_dict = {
                "outcome": {
                    "code": outcome_code,
                    "display": outcome_display,
                    "system": outcome_system,
                },
                "probability": probability,
                "qualitative_risk": qualitative_risk,
            }

            # Create method CodeableConcept if model info provided
            method = None
            if model_name:
                method = create_single_codeable_concept(
                    code=model_name,
                    display=f"{model_name} v{model_version}"
                    if model_version
                    else model_name,
                    system="https://healthchain.github.io/ml-models",
                )

            # Create comment with prediction details
            comment = (
                f"ML prediction: {'Positive' if prediction == 1 else 'Negative'} "
                f"(probability: {probability:.2%}, risk: {qualitative_risk})"
            )

            # Create RiskAssessment
            risk_assessment = create_risk_assessment_from_prediction(
                subject=patient_ref,
                prediction=prediction_dict,
                method=method,
                comment=comment,
            )

            risk_assessments.append(risk_assessment)

        return risk_assessments
