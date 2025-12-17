"""
Multi-EHR Data Aggregation Application

This application demonstrates how to use HealthChain's FHIRGateway to:
- Connect to multiple Electronic Health Record (EHR) systems
- Aggregate patient data from different sources
- Deduplicate and normalize healthcare data
- Export unified patient records for analysis

Use Cases:
- Patient 360 views across multiple healthcare providers
- Population health management
- Clinical research data aggregation
- Care coordination across health systems
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from pydantic import BaseModel, Field
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.condition import Condition
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.bundle import Bundle

from healthchain.gateway import AsyncFHIRGateway
from healthchain.fhir import get_resources
from healthchain.io.containers import DataContainer

from models.patient_record import AggregatedPatientRecord, EHRSource
from models.analytics import PatientAnalytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiEHRConfig(BaseModel):
    """Configuration for Multi-EHR aggregation"""

    ehr_sources: List[EHRSource] = Field(
        default_factory=list,
        description="List of EHR systems to connect to"
    )
    deduplication_enabled: bool = Field(
        default=True,
        description="Enable deduplication of resources"
    )
    normalize_codes: bool = Field(
        default=True,
        description="Normalize medical codes (ICD, SNOMED, LOINC)"
    )
    export_format: str = Field(
        default="json",
        description="Export format: json, csv, parquet"
    )


class MultiEHRAggregator:
    """
    Multi-EHR Data Aggregation Service

    Aggregates patient data from multiple EHR systems using HealthChain's
    FHIRGateway for seamless multi-source data integration.
    """

    def __init__(self, config: MultiEHRConfig):
        self.config = config
        self.gateways: Dict[str, AsyncFHIRGateway] = {}
        self.aggregated_data: Dict[str, AggregatedPatientRecord] = {}

    async def initialize_gateways(self):
        """Initialize FHIR gateways for each EHR source"""
        logger.info(f"Initializing {len(self.config.ehr_sources)} EHR gateways...")

        for source in self.config.ehr_sources:
            if not source.enabled:
                logger.info(f"⊘ Skipping disabled source: {source.name}")
                continue

            try:
                gateway = AsyncFHIRGateway()

                # Build connection string from source config
                # Format: fhir://hostname/path?client_id=...&client_secret=...&token_url=...
                connection_string = self._build_connection_string(source)
                gateway.add_source(source.name, connection_string)

                self.gateways[source.name] = gateway
                logger.info(f"✓ Connected to {source.name} ({source.system_type})")
            except Exception as e:
                logger.error(f"✗ Failed to connect to {source.name}: {e}")

    def _build_connection_string(self, source: EHRSource) -> str:
        """Build FHIR connection string from EHRSource configuration"""
        # Parse base_url to extract host and path
        from urllib.parse import urlparse, urlencode

        parsed = urlparse(source.base_url)

        # Start building the fhir:// connection string
        # For simple connections without auth, just use the base URL directly
        if source.auth_type == "none" or source.auth_type.value == "none":
            # For no-auth servers, use the URL as-is but with fhir:// scheme
            return f"fhir://{parsed.netloc}{parsed.path}"

        # For OAuth2, build connection string with credentials
        params = {}
        if source.credentials:
            params.update(source.credentials)

        if params:
            query_string = urlencode(params)
            return f"fhir://{parsed.netloc}{parsed.path}?{query_string}"

        return f"fhir://{parsed.netloc}{parsed.path}"

    async def aggregate_patient_data(
        self,
        patient_identifier: str,
        identifier_system: Optional[str] = None
    ) -> AggregatedPatientRecord:
        """
        Aggregate patient data from all configured EHR sources

        Args:
            patient_identifier: Patient ID or MRN
            identifier_system: Identifier system (e.g., MRN, SSN)

        Returns:
            AggregatedPatientRecord with unified patient data
        """
        logger.info(f"Aggregating data for patient: {patient_identifier}")

        aggregated_record = AggregatedPatientRecord(
            patient_identifier=patient_identifier,
            identifier_system=identifier_system
        )

        # Fetch data from each EHR source
        for source_name, gateway in self.gateways.items():
            try:
                patient_data = await self._fetch_patient_data(
                    gateway,
                    source_name,
                    patient_identifier
                )

                if patient_data:
                    aggregated_record.add_source_data(source_name, patient_data)
                    logger.info(f"✓ Retrieved data from {source_name}")
                else:
                    logger.warning(f"No data found in {source_name}")

            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
                aggregated_record.add_error(source_name, str(e))

        # Deduplicate if enabled
        if self.config.deduplication_enabled:
            aggregated_record.deduplicate_resources()

        # Normalize codes if enabled
        if self.config.normalize_codes:
            aggregated_record.normalize_codes()

        self.aggregated_data[patient_identifier] = aggregated_record

        logger.info(
            f"Aggregation complete: {len(aggregated_record.sources)} sources, "
            f"{len(aggregated_record.observations)} observations, "
            f"{len(aggregated_record.conditions)} conditions"
        )

        return aggregated_record

    async def _fetch_patient_data(
        self,
        gateway: AsyncFHIRGateway,
        source_name: str,
        patient_id: str
    ) -> Dict:
        """Fetch patient data from a single FHIR source"""

        patient_data = {
            "patient": None,
            "observations": [],
            "conditions": [],
            "medications": [],
            "procedures": [],
        }

        # Fetch Patient resource
        try:
            patient_bundle = await gateway.search(
                Patient,
                params={"identifier": patient_id},
                source=source_name
            )
            patients = get_resources(patient_bundle, Patient)
            if patients:
                patient_data["patient"] = patients[0]
        except Exception as e:
            logger.error(f"Error fetching Patient from {source_name}: {e}")

        # Fetch Observations
        try:
            obs_bundle = await gateway.search(
                Observation,
                params={"patient": patient_id, "_count": "100"},
                source=source_name
            )
            patient_data["observations"] = get_resources(obs_bundle, Observation)
        except Exception as e:
            logger.error(f"Error fetching Observations from {source_name}: {e}")

        # Fetch Conditions
        try:
            cond_bundle = await gateway.search(
                Condition,
                params={"patient": patient_id},
                source=source_name
            )
            patient_data["conditions"] = get_resources(cond_bundle, Condition)
        except Exception as e:
            logger.error(f"Error fetching Conditions from {source_name}: {e}")

        # Fetch MedicationRequests
        try:
            med_bundle = await gateway.search(
                MedicationRequest,
                params={"patient": patient_id},
                source=source_name
            )
            patient_data["medications"] = get_resources(med_bundle, MedicationRequest)
        except Exception as e:
            logger.error(f"Error fetching MedicationRequests from {source_name}: {e}")

        return patient_data

    def get_patient_analytics(self, patient_identifier: str) -> Optional[PatientAnalytics]:
        """Generate analytics for an aggregated patient record"""

        if patient_identifier not in self.aggregated_data:
            logger.warning(f"No aggregated data found for {patient_identifier}")
            return None

        record = self.aggregated_data[patient_identifier]
        return PatientAnalytics.from_aggregated_record(record)

    def export_data(self, output_path: Path, format: Optional[str] = None):
        """
        Export aggregated data to file

        Args:
            output_path: Output file path
            format: Export format (json, csv, parquet). If None, uses config setting
        """
        export_format = format or self.config.export_format

        logger.info(f"Exporting data to {output_path} ({export_format})...")

        if export_format == "json":
            self._export_json(output_path)
        elif export_format == "csv":
            self._export_csv(output_path)
        elif export_format == "parquet":
            self._export_parquet(output_path)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        logger.info(f"✓ Export complete: {output_path}")

    def _export_json(self, output_path: Path):
        """Export to JSON format"""
        import json

        data = {
            patient_id: record.model_dump(mode="json")
            for patient_id, record in self.aggregated_data.items()
        }

        output_path.write_text(json.dumps(data, indent=2))

    def _export_csv(self, output_path: Path):
        """Export to CSV format (flattened)"""
        import pandas as pd

        rows = []
        for patient_id, record in self.aggregated_data.items():
            # Create flattened rows for observations
            for obs in record.observations:
                rows.append({
                    "patient_id": patient_id,
                    "resource_type": "Observation",
                    "code": obs.code.text if obs.code else None,
                    "value": str(obs.value) if hasattr(obs, "value") else None,
                    "date": obs.effectiveDateTime if hasattr(obs, "effectiveDateTime") else None,
                    "source": getattr(obs, "_source", "unknown")
                })

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)

    def _export_parquet(self, output_path: Path):
        """Export to Parquet format for analytics"""
        import pandas as pd

        # Similar to CSV but save as parquet
        rows = []
        for patient_id, record in self.aggregated_data.items():
            for obs in record.observations:
                rows.append({
                    "patient_id": patient_id,
                    "resource_type": "Observation",
                    "code": obs.code.text if obs.code else None,
                    "value": str(obs.value) if hasattr(obs, "value") else None,
                    "date": obs.effectiveDateTime if hasattr(obs, "effectiveDateTime") else None,
                    "source": getattr(obs, "_source", "unknown")
                })

        df = pd.DataFrame(rows)
        df.to_parquet(output_path, index=False)


async def main():
    """Example usage of Multi-EHR Aggregator"""

    # Configure EHR sources
    config = MultiEHRConfig(
        ehr_sources=[
            EHRSource(
                name="Epic_MainHospital",
                base_url="https://fhir.epic.example.com/api/FHIR/R4",
                system_type="Epic",
                auth_type="oauth2"
            ),
            EHRSource(
                name="Cerner_CommunityClinic",
                base_url="https://fhir.cerner.example.com/r4",
                system_type="Cerner",
                auth_type="oauth2"
            ),
        ],
        deduplication_enabled=True,
        normalize_codes=True,
        export_format="json"
    )

    # Initialize aggregator
    aggregator = MultiEHRAggregator(config)
    await aggregator.initialize_gateways()

    # Aggregate patient data
    patient_record = await aggregator.aggregate_patient_data(
        patient_identifier="12345",
        identifier_system="MRN"
    )

    # Generate analytics
    analytics = aggregator.get_patient_analytics("12345")
    if analytics:
        print(f"\nPatient Analytics:")
        print(f"  Total Observations: {analytics.total_observations}")
        print(f"  Active Conditions: {analytics.active_conditions}")
        print(f"  Data Sources: {analytics.data_sources}")

    # Export data
    output_path = Path("data/aggregated_patients.json")
    aggregator.export_data(output_path)


if __name__ == "__main__":
    asyncio.run(main())
