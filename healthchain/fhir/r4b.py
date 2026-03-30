"""Version-aware re-exports for FHIR R4B resources.

Import FHIR R4B resource classes from here instead of fhir.resources directly:

    from healthchain.fhir.r4b import Condition, Patient, Appointment

This ensures version consistency with HealthChain's FHIR version management.
"""

from healthchain.fhir.version import get_fhir_resource as _get


def __getattr__(name: str):
    if name.startswith("__"):
        raise AttributeError(name)
    try:
        return _get(name, "R4B")
    except ValueError:
        raise AttributeError(f"module 'healthchain.fhir.r4b' has no attribute {name!r}")


__all__ = [  # noqa: F822
    # Clinical resources
    "AllergyIntolerance",
    "Appointment",
    "CarePlan",
    "CareTeam",
    "Condition",
    "DiagnosticReport",
    "DocumentReference",
    "Encounter",
    "FamilyMemberHistory",
    "Goal",
    "Immunization",
    "MedicationRequest",
    "MedicationStatement",
    "Observation",
    "Procedure",
    "Questionnaire",
    "QuestionnaireResponse",
    "RiskAssessment",
    "ServiceRequest",
    "Specimen",
    # Administrative resources
    "Device",
    "Location",
    "Organization",
    "Patient",
    "Practitioner",
    "Task",
    # Infrastructure resources
    "Bundle",
    "BundleEntry",
    "CapabilityStatement",
    "OperationOutcome",
    "Provenance",
    "ProvenanceAgent",
    # Element types
    "Address",
    "Annotation",
    "Attachment",
    "CodeableConcept",
    "Coding",
    "ContactPoint",
    "Dosage",
    "Extension",
    "HumanName",
    "Identifier",
    "Meta",
    "Period",
    "Quantity",
    "Range",
    "Reference",
    "Timing",
]
