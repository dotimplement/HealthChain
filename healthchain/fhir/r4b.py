"""Version-aware re-exports for FHIR R4B resources.

Import FHIR R4B resource classes from here instead of fhir.resources directly:

    from healthchain.fhir.r4b import Condition, Patient, Appointment

This ensures version consistency with HealthChain's FHIR version management.
"""

from healthchain.fhir.version import get_fhir_resource as _get


def __getattr__(name: str):
    return _get(name, "R4B")


__all__ = [  # noqa: F822
    "AllergyIntolerance",
    "Annotation",
    "Appointment",
    "Attachment",
    "Bundle",
    "BundleEntry",
    "CapabilityStatement",
    "CarePlan",
    "CodeableConcept",
    "Coding",
    "Condition",
    "ContactPoint",
    "DocumentReference",
    "Dosage",
    "Encounter",
    "HumanName",
    "Identifier",
    "MedicationRequest",
    "MedicationStatement",
    "Meta",
    "Observation",
    "OperationOutcome",
    "Patient",
    "Period",
    "Procedure",
    "Provenance",
    "ProvenanceAgent",
    "Reference",
    "RiskAssessment",
]
