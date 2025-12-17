"""
Patient Analytics Dashboard Example

Demonstrates generating comprehensive analytics and insights from
aggregated multi-EHR patient data.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import MultiEHRAggregator, MultiEHRConfig
from models.patient_record import EHRSource


def print_dashboard(analytics):
    """Print a formatted analytics dashboard"""

    print("\n" + "=" * 70)
    print("PATIENT ANALYTICS DASHBOARD".center(70))
    print("=" * 70)

    # Header
    print(f"\nPatient ID: {analytics.patient_identifier}")
    print(f"Analysis Date: {analytics.analysis_timestamp.strftime('%Y-%m-%d %H:%M')}")

    # Data Sources Section
    print("\n" + "-" * 70)
    print("DATA SOURCES")
    print("-" * 70)
    print(f"  Active Sources: {analytics.data_sources}")
    print(f"  Source Systems: {', '.join(analytics.source_names)}")
    if analytics.failed_sources > 0:
        print(f"  ⚠ Failed Sources: {analytics.failed_sources}")

    # Clinical Data Summary
    print("\n" + "-" * 70)
    print("CLINICAL DATA SUMMARY")
    print("-" * 70)
    print(f"  Observations:  {analytics.total_observations:4d}")
    print(f"  Conditions:    {analytics.total_conditions:4d} "
          f"({analytics.condition_stats.active_count if analytics.condition_stats else 0} active)")
    print(f"  Medications:   {analytics.total_medications:4d} "
          f"({analytics.medication_stats.active_count if analytics.medication_stats else 0} active)")
    print(f"  Procedures:    {analytics.total_procedures:4d}")

    # Observations Detail
    if analytics.observation_stats:
        print("\n" + "-" * 70)
        print("OBSERVATIONS DETAIL")
        print("-" * 70)
        stats = analytics.observation_stats
        print(f"  Total Count: {stats.total_count}")
        print(f"  Unique Types: {stats.unique_codes}")

        if stats.date_range:
            print(f"  Date Range: {stats.date_range['earliest'].strftime('%Y-%m-%d')} "
                  f"to {stats.date_range['latest'].strftime('%Y-%m-%d')}")

        if stats.most_common:
            print(f"\n  Most Common Observations:")
            for obs in stats.most_common[:5]:
                print(f"    • {obs['code']}: {obs['count']} times")

    # Conditions Detail
    if analytics.condition_stats and analytics.condition_stats.chronic_conditions:
        print("\n" + "-" * 70)
        print("CHRONIC CONDITIONS")
        print("-" * 70)
        for condition in analytics.condition_stats.chronic_conditions:
            print(f"  • {condition}")

    # Data Quality Metrics
    print("\n" + "-" * 70)
    print("DATA QUALITY METRICS")
    print("-" * 70)
    print(f"  Completeness: {analytics.completeness_score:.1%}")
    if analytics.data_freshness_days is not None:
        freshness_status = "✓ Current" if analytics.data_freshness_days < 30 else "⚠ Outdated"
        print(f"  Data Freshness: {analytics.data_freshness_days} days ({freshness_status})")
    print(f"  Duplicates Removed: {analytics.duplicate_resources}")

    # Risk Flags
    if analytics.risk_flags:
        print("\n" + "-" * 70)
        print("⚠ RISK FLAGS")
        print("-" * 70)
        for risk in analytics.risk_flags:
            print(f"  ! {risk}")

    # Care Gaps
    if analytics.care_gaps:
        gaps = analytics.care_gaps

        if gaps.missing_screenings or gaps.overdue_labs:
            print("\n" + "-" * 70)
            print("CARE GAPS & OPPORTUNITIES")
            print("-" * 70)

            if gaps.missing_screenings:
                print("  Missing Screenings:")
                for screening in gaps.missing_screenings:
                    print(f"    • {screening}")

            if gaps.overdue_labs:
                print("  Overdue Laboratory Tests:")
                for lab in gaps.overdue_labs:
                    print(f"    • {lab}")

    print("\n" + "=" * 70 + "\n")


async def main():
    """Analytics dashboard example"""

    print("Multi-EHR Data Aggregation - Analytics Dashboard")

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
        normalize_codes=True,
    )

    # Create aggregator and initialize
    aggregator = MultiEHRAggregator(config)
    await aggregator.initialize_gateways()

    # Aggregate patient data
    patient_id = "example"
    print(f"\nAggregating data for patient: {patient_id}...")

    patient_record = await aggregator.aggregate_patient_data(
        patient_identifier=patient_id,
        identifier_system="MRN"
    )

    # Generate analytics
    analytics = aggregator.get_patient_analytics(patient_id)

    if analytics:
        # Display dashboard
        print_dashboard(analytics)

        # Also show text summary
        # print(analytics.generate_summary())


if __name__ == "__main__":
    asyncio.run(main())
