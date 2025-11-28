"""Schema-driven FHIR to feature mapper for ML model deployment.

This module provides schema-driven feature extraction from FHIR Bundles,
using FeatureSchema to specify which features to extract and how to transform them.
"""

from typing import Any, Dict, Union
import pandas as pd
import numpy as np

from fhir.resources.bundle import Bundle

from healthchain.io.containers.featureschema import FeatureSchema
from healthchain.io.mappers.base import BaseMapper
from healthchain.fhir.dataframe import bundle_to_dataframe, BundleConverterConfig


class FHIRFeatureMapper(BaseMapper[Bundle, pd.DataFrame]):
    """Schema-driven mapper from FHIR resources to DataFrame features.

    Uses a FeatureSchema to extract and transform specific features from FHIR Bundles.
    Leverages the generic bundle_to_dataframe converter and filters/renames columns
    based on the schema.
    """

    def __init__(self, schema: FeatureSchema):
        self.schema = schema

    def map(self, source: Bundle) -> pd.DataFrame:
        """Transform FHIR Bundle to DataFrame using default aggregation.
        Args:
            source: FHIR Bundle resource

        Returns:
            DataFrame with extracted features
        """
        return self.extract_features(source)

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
        # Build config from schema
        config = self._build_config_from_schema(aggregation)

        # Extract features using config
        df = bundle_to_dataframe(bundle, config=config)

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

    def _build_config_from_schema(self, aggregation: str) -> BundleConverterConfig:
        """Build converter config from feature schema.

        Args:
            aggregation: Aggregation method for observations

        Returns:
            BundleConverterConfig configured based on schema
        """
        # Determine which resources are needed from schema
        resources = set()
        for feature in self.schema.features.values():
            resources.add(feature.fhir_resource)

        # Extract age calculation metadata if present
        metadata = self.schema.metadata or {}
        age_calculation = metadata.get("age_calculation", "current_date")
        event_date_source = metadata.get("event_date_source", "Observation")
        event_date_strategy = metadata.get("event_date_strategy", "earliest")

        return BundleConverterConfig(
            resources=list(resources),
            observation_aggregation=aggregation,
            age_calculation=age_calculation,
            event_date_source=event_date_source,
            event_date_strategy=event_date_strategy,
        )

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
