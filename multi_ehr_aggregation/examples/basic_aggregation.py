"""
Basic Multi-EHR Data Aggregation Example

Demonstrates simple patient data aggregation from multiple EHR sources.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import MultiEHRAggregator, MultiEHRConfig
from models.patient_record import EHRSource


async def main():
    """Basic aggregation example"""

    print("=" * 60)
    print("Multi-EHR Data Aggregation - Basic Example")
    print("=" * 60)

    # Configure EHR sources
    config = MultiEHRConfig(
        ehr_sources=[
            # Using public FHIR test server
            EHRSource(
                name="HAPI_FHIR",
                base_url="http://hapi.fhir.org/baseR4",
                system_type="Generic_FHIR",
                auth_type="none",
                enabled=True,
                priority=1
            ),
        ],
        deduplication_enabled=True,
        normalize_codes=False,
        export_format="json"
    )

    # Create aggregator
    aggregator = MultiEHRAggregator(config)

    # Initialize connections
    print("\n1. Initializing EHR connections...")
    await aggregator.initialize_gateways()

    # Aggregate patient data
    print("\n2. Aggregating patient data...")
    patient_id = "example"  # Use a test patient ID

    try:
        patient_record = await aggregator.aggregate_patient_data(
            patient_identifier=patient_id,
            identifier_system="MRN"
        )

        print(f"\n3. Aggregation Results:")
        print(f"   - Patient ID: {patient_record.patient_identifier}")
        print(f"   - Data Sources: {len(patient_record.sources)}")
        print(f"   - Observations: {len(patient_record.observations)}")
        print(f"   - Conditions: {len(patient_record.conditions)}")
        print(f"   - Medications: {len(patient_record.medications)}")

        # Generate analytics
        print("\n4. Generating Analytics...")
        analytics = aggregator.get_patient_analytics(patient_id)

        if analytics:
            print(analytics.generate_summary())

        # Export data
        print("\n5. Exporting Data...")
        output_path = Path("data/basic_example_output.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        aggregator.export_data(output_path)

        print(f"\n✓ Complete! Data exported to: {output_path}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
