"""
Batch Multi-EHR Data Aggregation Example

Demonstrates aggregating data for multiple patients in batch.
"""

import asyncio
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import MultiEHRAggregator, MultiEHRConfig
from models.patient_record import EHRSource


async def aggregate_patient_batch(
    aggregator: MultiEHRAggregator,
    patient_ids: List[str]
) -> dict:
    """Aggregate data for a batch of patients"""

    results = {
        "successful": [],
        "failed": [],
        "summary": {}
    }

    print(f"\nProcessing {len(patient_ids)} patients...")

    for i, patient_id in enumerate(patient_ids, 1):
        print(f"\n[{i}/{len(patient_ids)}] Processing patient: {patient_id}")

        try:
            record = await aggregator.aggregate_patient_data(
                patient_identifier=patient_id,
                identifier_system="MRN"
            )

            results["successful"].append({
                "patient_id": patient_id,
                "sources": len(record.sources),
                "observations": len(record.observations),
                "conditions": len(record.conditions),
                "medications": len(record.medications)
            })

            print(f"  ✓ Success - {len(record.observations)} obs, "
                  f"{len(record.conditions)} conditions")

        except Exception as e:
            results["failed"].append({
                "patient_id": patient_id,
                "error": str(e)
            })
            print(f"  ✗ Failed: {e}")

    # Generate summary
    results["summary"] = {
        "total_patients": len(patient_ids),
        "successful": len(results["successful"]),
        "failed": len(results["failed"]),
        "success_rate": len(results["successful"]) / len(patient_ids) * 100
    }

    return results


async def main():
    """Batch aggregation example"""

    print("=" * 60)
    print("Multi-EHR Data Aggregation - Batch Processing")
    print("=" * 60)

    # Configure EHR sources
    config = MultiEHRConfig(
        ehr_sources=[
            EHRSource(
                name="HAPI_FHIR",
                base_url="http://hapi.fhir.org/baseR4",
                system_type="Generic_FHIR",
                auth_type="none"
            ),
        ],
        deduplication_enabled=True,
        export_format="json"
    )

    # Create aggregator
    aggregator = MultiEHRAggregator(config)
    await aggregator.initialize_gateways()

    # Patient IDs to process
    patient_ids = [
        "example",
        "test-patient-1",
        "test-patient-2",
        # Add more patient IDs as needed
    ]

    # Run batch aggregation
    results = await aggregate_patient_batch(aggregator, patient_ids)

    # Print summary
    print("\n" + "=" * 60)
    print("Batch Processing Summary")
    print("=" * 60)
    print(f"Total Patients: {results['summary']['total_patients']}")
    print(f"Successful: {results['summary']['successful']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Success Rate: {results['summary']['success_rate']:.1f}%")

    # Export all aggregated data
    if results["successful"]:
        output_path = Path("data/batch_aggregation_output.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        aggregator.export_data(output_path)
        print(f"\n✓ Data exported to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
