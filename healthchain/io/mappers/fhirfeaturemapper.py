"""Schema-driven FHIR to feature mapper for ML model deployment.

This module provides schema-driven feature extraction from FHIR Bundles,
using FeatureSchema to specify which features to extract and how to transform them.
"""

from typing import Any, Dict, Union
import pandas as pd
import numpy as np

from fhir.resources.bundle import Bundle

from healthchain.io.containers.featureschema import FeatureSchema
from healthchain.fhir.converters import bundle_to_dataframe


class FHIRFeatureMapper:
    """Schema-driven mapper from FHIR resources to DataFrame features.

    Uses a FeatureSchema to extract and transform specific features from FHIR Bundles.
    Leverages the generic bundle_to_dataframe converter and filters/renames columns
    based on the schema.
    """

    def __init__(self, schema: FeatureSchema):
        self.schema = schema

    def extract_features(
        self,
        bundle: Union[Bundle, Dict[str, Any]],
        aggregation: str = "mean",
    ) -> pd.DataFrame:
        """Extract features from a FHIR Bundle according to the schema.

        Args:
            bundle: FHIR Bundle resource (object or dict)
            aggregation: How to aggregate multiple observation values (default: "mean")
                Options: "mean", "median", "max", "min", "last" (default: "mean")

        Returns:
            DataFrame with one row per patient and columns matching schema features

        Example:
            >>> from healthchain.io.containers.featureschema import FeatureSchema
            >>> schema = FeatureSchema.from_yaml("configs/features/sepsis_vitals.yaml")
            >>> mapper = FHIRFeatureMapper(schema)
            >>> df = mapper.extract_features(bundle)
        """
        # Extract age calculation metadata if present
        metadata = self.schema.metadata or {}
        age_calculation = metadata.get("age_calculation", "current_date")
        use_event_date = age_calculation == "event_date"
        event_date_source = metadata.get("event_date_source", "Observation")
        event_date_strategy = metadata.get("event_date_strategy", "earliest")

        df = bundle_to_dataframe(
            bundle,
            include_patient=True,
            include_observations=True,
            include_conditions=False,
            include_medications=False,
            observation_aggregation=aggregation,
            use_event_date_for_age=use_event_date,
            event_date_source=event_date_source,
            event_date_strategy=event_date_strategy,
        )

        if df.empty:
            return pd.DataFrame(
                columns=["patient_ref"] + self.schema.get_feature_names()
            )

        # Map generic column names to schema feature names
        df_mapped = self._map_columns_to_schema(df)

        # Ensure all schema features are present (fill missing with NaN)
        feature_names = self.schema.get_feature_names()
        for feature in feature_names:
            if feature not in df_mapped.columns:
                df_mapped[feature] = np.nan

        # Reorder columns to match schema
        df_mapped = df_mapped[["patient_ref"] + feature_names]

        return df_mapped

    def _map_columns_to_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map generic DataFrame columns to schema feature names.

        Args:
            df: DataFrame from bundle_to_dataframe

        Returns:
            DataFrame with columns renamed according to schema
        """
        rename_map = {}

        # Map observation columns
        obs_features = self.schema.get_features_by_resource("Observation")
        for feature_name, mapping in obs_features.items():
            # Generic converter creates columns like: "8867-4_Heart_rate"
            # Find matching column in df
            for col in df.columns:
                if col.startswith(mapping.code):
                    rename_map[col] = feature_name
                    break

        # Map patient columns (already have correct names from helpers)
        patient_features = self.schema.get_features_by_resource("Patient")
        for feature_name, mapping in patient_features.items():
            if mapping.field == "birthDate":
                # Generic converter uses "age"
                if "age" in df.columns:
                    rename_map["age"] = feature_name
            elif mapping.field == "gender":
                # Generic converter uses "gender"
                if "gender" in df.columns:
                    rename_map["gender"] = feature_name

        # Rename columns
        df_renamed = df.rename(columns=rename_map)

        return df_renamed
