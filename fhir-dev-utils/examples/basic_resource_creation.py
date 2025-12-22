"""
Basic FHIR Resource Creation Example

Demonstrates type-safe creation of FHIR resources using the builder pattern.
"""

import sys
sys.path.insert(0, "..")

from fhir_utils import (
    ResourceFactory,
    PatientBuilder,
    ConditionBuilder,
    ObservationBuilder,
    MedicationStatementBuilder,
    AllergyIntoleranceBuilder,
)
from fhir_utils.bundle_tools import BundleBuilder


def create_patient_example():
    """Create a patient with various demographic information."""
    print("=== Creating Patient ===\n")

    # Method 1: Using ResourceFactory
    patient = ResourceFactory.patient() \
        .with_id("patient-001") \
        .with_name("Smith", given=["John", "Robert"], prefix=["Mr."]) \
        .with_birth_date("1985-03-15") \
        .with_gender("male") \
        .with_mrn("MRN123456", system="http://hospital.example.org/mrn") \
        .with_contact(phone="555-123-4567", email="john.smith@email.com") \
        .with_address(
            line=["123 Main Street", "Apt 4B"],
            city="Boston",
            state="MA",
            postal_code="02101",
            country="USA"
        ) \
        .active() \
        .build()

    print(f"Patient ID: {patient.id}")
    print(f"Name: {patient.name[0].family}, {' '.join(patient.name[0].given)}")
    print(f"Gender: {patient.gender}")
    print(f"Birth Date: {patient.birthDate}")
    print(f"Active: {patient.active}\n")

    return patient


def create_condition_example(patient_id: str):
    """Create conditions associated with a patient."""
    print("=== Creating Conditions ===\n")

    # Diabetes condition using SNOMED CT
    diabetes = ResourceFactory.condition() \
        .for_patient(patient_id) \
        .with_snomed("73211009", "Diabetes mellitus") \
        .with_clinical_status("active") \
        .with_verification_status("confirmed") \
        .with_category("encounter-diagnosis") \
        .with_onset("2020-06-15") \
        .with_severity("moderate") \
        .with_note("Type 2 diabetes, well controlled with medication") \
        .build()

    print(f"Condition: {diabetes.code.coding[0].display}")
    print(f"Clinical Status: {diabetes.clinicalStatus.coding[0].code}")
    print(f"Onset: {diabetes.onsetDateTime}\n")

    # Hypertension using ICD-10
    hypertension = ResourceFactory.condition() \
        .for_patient(patient_id) \
        .with_icd10("I10", "Essential (primary) hypertension") \
        .with_clinical_status("active") \
        .with_verification_status("confirmed") \
        .build()

    print(f"Condition: {hypertension.code.coding[0].display}")
    print(f"Code System: {hypertension.code.coding[0].system}\n")

    return [diabetes, hypertension]


def create_observation_example(patient_id: str):
    """Create observations (vitals, labs) for a patient."""
    print("=== Creating Observations ===\n")

    # Blood pressure observation
    systolic_bp = ResourceFactory.observation() \
        .with_id("obs-bp-systolic") \
        .for_patient(patient_id) \
        .with_loinc("8480-6", "Systolic blood pressure") \
        .with_value_quantity(120, "mm[Hg]") \
        .with_status("final") \
        .with_category("vital-signs") \
        .with_effective_datetime("2024-01-15T10:30:00Z") \
        .with_reference_range(low=90, high=140, unit="mm[Hg]") \
        .with_interpretation("N") \
        .build()

    print(f"Observation: {systolic_bp.code.coding[0].display}")
    print(f"Value: {systolic_bp.valueQuantity.value} {systolic_bp.valueQuantity.unit}")
    print(f"Interpretation: {systolic_bp.interpretation[0].coding[0].display}\n")

    # Glucose lab result
    glucose = ResourceFactory.observation() \
        .for_patient(patient_id) \
        .with_loinc("2339-0", "Glucose [Mass/volume] in Blood") \
        .with_value_quantity(95, "mg/dL") \
        .with_category("laboratory") \
        .with_reference_range(low=70, high=100, unit="mg/dL", text="Normal fasting glucose") \
        .with_interpretation("N") \
        .build()

    print(f"Lab: {glucose.code.coding[0].display}")
    print(f"Value: {glucose.valueQuantity.value} {glucose.valueQuantity.unit}\n")

    return [systolic_bp, glucose]


def create_medication_example(patient_id: str):
    """Create medication statements for a patient."""
    print("=== Creating Medications ===\n")

    metformin = ResourceFactory.medication_statement() \
        .for_patient(patient_id) \
        .with_rxnorm("197361", "Metformin 500 MG Oral Tablet") \
        .with_status("active") \
        .with_effective_period("2020-06-20") \
        .with_dosage(
            text="Take 500mg twice daily with meals",
            route="26643006",
            route_display="Oral route",
            dose_value=500,
            dose_unit="mg"
        ) \
        .with_reason("73211009", "http://snomed.info/sct", "Diabetes mellitus") \
        .build()

    print(f"Medication: {metformin.medicationCodeableConcept.coding[0].display}")
    print(f"Status: {metformin.status}")
    print(f"Dosage: {metformin.dosage[0].text}\n")

    return [metformin]


def create_allergy_example(patient_id: str):
    """Create allergy information for a patient."""
    print("=== Creating Allergies ===\n")

    penicillin_allergy = ResourceFactory.allergy_intolerance() \
        .for_patient(patient_id) \
        .with_code("91936005", "http://snomed.info/sct", "Allergy to penicillin") \
        .with_clinical_status("active") \
        .with_verification_status("confirmed") \
        .with_type("allergy") \
        .with_category("medication") \
        .with_criticality("high") \
        .with_reaction(
            manifestation_code="271807003",
            manifestation_display="Skin rash",
            severity="moderate",
            description="Developed generalized rash within 2 hours of taking penicillin"
        ) \
        .build()

    print(f"Allergy: {penicillin_allergy.code.coding[0].display}")
    print(f"Criticality: {penicillin_allergy.criticality}")
    print(f"Reaction: {penicillin_allergy.reaction[0].manifestation[0].coding[0].display}\n")

    return [penicillin_allergy]


def create_bundle_example(resources: list):
    """Create a bundle containing all resources."""
    print("=== Creating Bundle ===\n")

    bundle = BundleBuilder() \
        .with_id("example-bundle-001") \
        .with_timestamp() \
        .as_collection() \
        .add_all(resources) \
        .build()

    print(f"Bundle ID: {bundle.id}")
    print(f"Bundle Type: {bundle.type}")
    print(f"Total Entries: {bundle.total}")
    print(f"Timestamp: {bundle.timestamp}\n")

    return bundle


def main():
    """Main function demonstrating all resource creation examples."""
    print("\n" + "=" * 60)
    print("FHIR Resource Creation Examples")
    print("=" * 60 + "\n")

    # Create patient
    patient = create_patient_example()

    # Create associated resources
    conditions = create_condition_example(patient.id)
    observations = create_observation_example(patient.id)
    medications = create_medication_example(patient.id)
    allergies = create_allergy_example(patient.id)

    # Combine into bundle
    all_resources = [patient] + conditions + observations + medications + allergies
    bundle = create_bundle_example(all_resources)

    # Output as JSON
    print("=== Bundle JSON (first 1000 chars) ===\n")
    json_output = bundle.model_dump_json(indent=2, exclude_none=True)
    print(json_output[:1000] + "...\n")

    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
