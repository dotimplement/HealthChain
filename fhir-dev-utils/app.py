"""
FHIR Development Utilities - Main Application

A comprehensive toolkit for accelerating healthcare application development
with type-safe FHIR resource creation, validation helpers, and sandbox
environments for testing clinical workflows.
"""

import argparse
import sys
from typing import Optional

from fhir_utils import (
    ResourceFactory,
    FHIRValidator,
    validate_resource,
    validate_bundle,
    BundleBuilder,
    BundleAnalyzer,
)
from sandbox import (
    FHIRSandbox,
    SyntheticDataGenerator,
    create_test_bundle,
    generate_synthetic_data,
)


def demo_resource_creation():
    """Demonstrate type-safe resource creation."""
    print("\n=== Type-Safe Resource Creation ===\n")

    # Create a patient with builder pattern
    patient = ResourceFactory.patient() \
        .with_id("demo-patient-001") \
        .with_name("Smith", given=["John", "Robert"]) \
        .with_birth_date("1985-03-15") \
        .with_gender("male") \
        .with_mrn("MRN123456") \
        .active() \
        .build()

    print(f"Created Patient: {patient.name[0].family}, {patient.name[0].given[0]}")
    print(f"  ID: {patient.id}")
    print(f"  Gender: {patient.gender}")
    print(f"  Birth Date: {patient.birthDate}")

    # Create associated condition
    condition = ResourceFactory.condition() \
        .for_patient(patient.id) \
        .with_snomed("73211009", "Diabetes mellitus") \
        .with_clinical_status("active") \
        .with_verification_status("confirmed") \
        .build()

    print(f"\nCreated Condition: {condition.code.coding[0].display}")
    print(f"  Patient: {condition.subject.reference}")

    # Create observation
    observation = ResourceFactory.observation() \
        .for_patient(patient.id) \
        .with_loinc("2339-0", "Glucose") \
        .with_value_quantity(95, "mg/dL") \
        .with_status("final") \
        .build()

    print(f"\nCreated Observation: {observation.code.coding[0].display}")
    print(f"  Value: {observation.valueQuantity.value} {observation.valueQuantity.unit}")


def demo_validation():
    """Demonstrate validation helpers."""
    print("\n=== Validation Helpers ===\n")

    validator = FHIRValidator()

    # Valid patient
    valid_patient = ResourceFactory.patient() \
        .with_name("Doe", given=["Jane"]) \
        .with_gender("female") \
        .build()

    result = validator.validate(valid_patient)
    print(f"Valid Patient: {result.is_valid} (warnings: {result.warning_count})")

    # Invalid condition (missing subject)
    invalid_dict = {
        "resourceType": "Condition",
        "code": {"text": "Some condition"}
    }

    result = validator.validate(invalid_dict)
    print(f"Invalid Condition: {result.is_valid} (errors: {result.error_count})")
    for error in result.errors[:2]:  # Show first 2 errors
        print(f"  - {error.message}")


def demo_bundle_operations():
    """Demonstrate bundle manipulation."""
    print("\n=== Bundle Operations ===\n")

    # Create bundle with builder
    patient = ResourceFactory.patient() \
        .with_id("bundle-demo-patient") \
        .with_name("Bundle", given=["Demo"]) \
        .build()

    condition1 = ResourceFactory.condition() \
        .for_patient(patient.id) \
        .with_snomed("38341003", "Hypertension") \
        .build()

    condition2 = ResourceFactory.condition() \
        .for_patient(patient.id) \
        .with_snomed("195967001", "Asthma") \
        .build()

    bundle = BundleBuilder() \
        .as_collection() \
        .add(patient) \
        .add(condition1) \
        .add(condition2) \
        .build()

    print(f"Created Bundle:")
    print(f"  Type: {bundle.type}")
    print(f"  Total entries: {bundle.total}")

    # Analyze bundle
    analyzer = BundleAnalyzer(bundle)
    print(f"\nBundle Analysis:")
    print(f"  Resource types: {', '.join(analyzer.resource_types)}")
    print(f"  Resource counts: {analyzer.get_resource_counts()}")


def demo_sandbox():
    """Demonstrate sandbox environment."""
    print("\n=== Sandbox Environment ===\n")

    # Create sandbox with reproducible data
    sandbox = FHIRSandbox(seed=42)

    # Generate test data
    bundle = sandbox.generate_test_data(num_patients=5)
    print(f"Generated {len(bundle.entry)} resources")

    # Query mock server
    patients = sandbox.server.search("Patient", {})
    print(f"Patients in server: {len(patients.entry)}")

    # Validate a sample resource
    sample = bundle.entry[0].resource
    result = sandbox.validator.validate(sample)
    print(f"Sample validation: {'VALID' if result.is_valid else 'INVALID'}")


def demo_synthetic_data():
    """Demonstrate synthetic data generation."""
    print("\n=== Synthetic Data Generation ===\n")

    generator = SyntheticDataGenerator(seed=123)

    # Generate single patient
    patient = generator.generate_patient(gender="female", age_range=(25, 45))
    print(f"Generated Patient: {patient.name[0].given[0]} {patient.name[0].family}")
    print(f"  Gender: {patient.gender}")
    print(f"  Birth Date: {patient.birthDate}")

    # Generate population
    population = generator.generate_population_bundle(num_patients=10)
    analyzer = BundleAnalyzer(population)
    print(f"\nPopulation Bundle:")
    print(f"  Patients: {len(analyzer.get_resources('Patient'))}")
    print(f"  Conditions: {len(analyzer.get_resources('Condition'))}")
    print(f"  Observations: {len(analyzer.get_resources('Observation'))}")


def run_demo(component: Optional[str] = None):
    """Run demonstration of utilities."""
    print("=" * 60)
    print("FHIR Development Utilities Demo")
    print("=" * 60)

    demos = {
        "resources": demo_resource_creation,
        "validation": demo_validation,
        "bundles": demo_bundle_operations,
        "sandbox": demo_sandbox,
        "synthetic": demo_synthetic_data,
    }

    if component and component in demos:
        demos[component]()
    else:
        for demo_fn in demos.values():
            demo_fn()

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="FHIR Development Utilities - Accelerate healthcare app development"
    )

    parser.add_argument(
        "command",
        choices=["demo", "generate", "validate"],
        help="Command to run"
    )

    parser.add_argument(
        "--component",
        choices=["resources", "validation", "bundles", "sandbox", "synthetic"],
        help="Specific component to demo"
    )

    parser.add_argument(
        "--patients",
        type=int,
        default=5,
        help="Number of patients to generate"
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility"
    )

    parser.add_argument(
        "--output",
        help="Output file for generated data"
    )

    args = parser.parse_args()

    if args.command == "demo":
        run_demo(args.component)

    elif args.command == "generate":
        print("Generating synthetic FHIR data...")
        bundle = generate_synthetic_data(
            num_patients=args.patients,
            seed=args.seed
        )
        print(f"Generated {len(bundle.entry)} resources")

        if args.output:
            with open(args.output, "w") as f:
                f.write(bundle.model_dump_json(indent=2, exclude_none=True))
            print(f"Saved to {args.output}")
        else:
            print("\nBundle JSON preview:")
            print(bundle.model_dump_json(indent=2, exclude_none=True)[:500] + "...")

    elif args.command == "validate":
        print("Validation mode - provide FHIR JSON to validate")
        # Read from stdin if available
        if not sys.stdin.isatty():
            import json
            data = json.load(sys.stdin)
            result = validate_resource(data)
            print(result)
        else:
            print("Usage: cat resource.json | python app.py validate")


if __name__ == "__main__":
    main()
