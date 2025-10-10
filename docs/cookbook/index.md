# Examples

The best way to learn is by example! Here are some to get you started:

## Getting Started

- [Working with FHIR Sandboxes](./setup_fhir_sandboxes.md): Set up access to Epic, Medplum, and other FHIR sandboxes for testing and development. Essential prerequisite for the tutorials below.

## Tutorials

- [Multi-Source Patient Data Aggregation](./data_aggregation.md): Aggregate patient data from multiple FHIR sources (Epic, Cerner), deduplicate conditions, track data provenance, and build production-ready error handling for cross-vendor healthcare AI applications.
- [Automate Clinical Coding and FHIR Integration](./clinical_coding.md): Build a system that extracts medical conditions from clinical documentation, maps them to SNOMED CT codes, and synchronizes structured Condition resources with external FHIR servers (Medplum) for billing and analytics.
- [Summarize Discharge Notes with CDS Hooks](./discharge_summarizer.md): Implement a CDS Hooks service that listens for `encounter-discharge` events, automatically generates concise summaries of discharge notes, and delivers clinical recommendations directly into EHR workflows.
