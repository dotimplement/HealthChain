"""
Sandbox Testing Example

Demonstrates using the sandbox environment for testing clinical workflows
without connecting to real EHR systems.
"""

import sys
sys.path.insert(0, "..")

from sandbox import (
    FHIRSandbox,
    MockFHIRServer,
    SyntheticDataGenerator,
    WorkflowTester,
    create_test_patient,
    create_test_bundle,
    generate_synthetic_data,
)
from fhir_utils import ResourceFactory
from fhir_utils.bundle_tools import BundleBuilder, BundleAnalyzer


def synthetic_data_generation_example():
    """Generate synthetic FHIR data for testing."""
    print("=== Synthetic Data Generation ===\n")

    # Create generator with seed for reproducibility
    generator = SyntheticDataGenerator(seed=42)

    # Generate single patient
    patient = generator.generate_patient(gender="female", age_range=(30, 50))
    print(f"Generated patient: {patient.name[0].family}, {patient.name[0].given[0]}")
    print(f"Gender: {patient.gender}")
    print(f"Birth Date: {patient.birthDate}\n")

    # Generate condition for patient
    condition = generator.generate_condition(patient.id)
    print(f"Generated condition: {condition.code.coding[0].display}")
    print(f"Onset: {condition.onsetDateTime}\n")

    # Generate observation
    observation = generator.generate_observation(patient.id)
    print(f"Generated observation: {observation.code.coding[0].display}")
    print(f"Value: {observation.valueQuantity.value} {observation.valueQuantity.unit}\n")


def patient_bundle_generation():
    """Generate complete patient bundles."""
    print("=== Patient Bundle Generation ===\n")

    generator = SyntheticDataGenerator(seed=123)

    # Generate bundle for single patient with all resource types
    bundle = generator.generate_patient_bundle(
        num_conditions=3,
        num_observations=5,
        num_medications=2,
        num_allergies=1
    )

    analyzer = BundleAnalyzer(bundle)

    print(f"Bundle generated with {analyzer.total} resources:")
    for res_type, count in analyzer.get_resource_counts().items():
        print(f"  - {res_type}: {count}")
    print()


def population_bundle_generation():
    """Generate bundles for multiple patients."""
    print("=== Population Bundle Generation ===\n")

    generator = SyntheticDataGenerator(seed=456)

    # Generate population of 5 patients
    bundle = generator.generate_population_bundle(
        num_patients=5,
        resources_per_patient={
            "conditions": 2,
            "observations": 4,
            "medications": 1,
            "allergies": 1,
        }
    )

    analyzer = BundleAnalyzer(bundle)

    print(f"Population bundle summary:")
    print(f"  Total resources: {analyzer.total}")
    print(f"  Patients: {len(analyzer.get_resources('Patient'))}")
    print(f"  Resource types: {', '.join(analyzer.resource_types)}\n")


def mock_server_example():
    """Using the mock FHIR server."""
    print("=== Mock FHIR Server ===\n")

    server = MockFHIRServer()

    # Create resources
    patient = ResourceFactory.patient() \
        .with_id("mock-patient-001") \
        .with_name("Mock", given=["Patient"]) \
        .with_gender("male") \
        .build()

    created_patient = server.create(patient)
    print(f"Created patient: {created_patient.id}")

    # Read resource
    retrieved = server.read("Patient", "mock-patient-001")
    print(f"Retrieved patient: {retrieved.name[0].family}")

    # Create associated condition
    condition = ResourceFactory.condition() \
        .for_patient("mock-patient-001") \
        .with_snomed("73211009", "Diabetes mellitus") \
        .build()

    server.create(condition)

    # Search for conditions
    results = server.search("Condition", {"patient": "Patient/mock-patient-001"})
    print(f"Found {len(results.entry)} condition(s) for patient")

    # Check operation history
    history = server.get_history()
    print(f"\nServer operations: {len(history)}")
    for op in history:
        print(f"  - {op['operation']} {op['resourceType']}/{op['id']}")
    print()


def transaction_bundle_example():
    """Execute transaction bundles on mock server."""
    print("=== Transaction Bundle Execution ===\n")

    server = MockFHIRServer()

    # Create transaction bundle
    patient = ResourceFactory.patient() \
        .with_id("tx-patient") \
        .with_name("Transaction", given=["Test"]) \
        .build()

    condition = ResourceFactory.condition() \
        .for_patient("tx-patient") \
        .with_snomed("38341003", "Hypertension") \
        .build()

    observation = ResourceFactory.observation() \
        .for_patient("tx-patient") \
        .with_loinc("8480-6", "Systolic BP") \
        .with_value_quantity(140, "mm[Hg]") \
        .build()

    bundle = BundleBuilder() \
        .as_transaction() \
        .add(patient, method="POST") \
        .add(condition, method="POST") \
        .add(observation, method="POST") \
        .build()

    # Execute transaction
    response = server.execute_bundle(bundle)

    print(f"Transaction executed:")
    print(f"  Request entries: {len(bundle.entry)}")
    print(f"  Response entries: {len(response.entry)}")

    # Verify resources were created
    all_patients = server.search("Patient", {})
    all_conditions = server.search("Condition", {})

    print(f"\nServer state after transaction:")
    print(f"  Patients: {len(all_patients.entry)}")
    print(f"  Conditions: {len(all_conditions.entry)}")
    print()


def workflow_testing_example():
    """Testing clinical workflows."""
    print("=== Workflow Testing ===\n")

    tester = WorkflowTester()

    # Setup test data
    test_bundle = create_test_bundle(
        num_patients=3,
        conditions_per_patient=2,
        observations_per_patient=3
    )
    loaded = tester.setup(test_bundle)
    print(f"Loaded {loaded} resources for testing")

    # Define and run tests
    def test_patient_exists(t: WorkflowTester) -> bool:
        """Test that patients were loaded."""
        results = t.server.search("Patient", {})
        return len(results.entry) >= 3

    def test_conditions_linked(t: WorkflowTester) -> bool:
        """Test that conditions are linked to patients."""
        patients = t.server.search("Patient", {})
        for entry in patients.entry:
            patient_id = entry.resource.id
            conditions = t.server.search("Condition", {"patient": f"Patient/{patient_id}"})
            if len(conditions.entry) == 0:
                return False
        return True

    def test_observation_values(t: WorkflowTester) -> bool:
        """Test that observations have valid values."""
        observations = t.server.search("Observation", {})
        for entry in observations.entry:
            obs = entry.resource
            if not hasattr(obs, "valueQuantity") or obs.valueQuantity is None:
                return False
            if obs.valueQuantity.value is None:
                return False
        return True

    # Run tests
    tester.run_test("patients_loaded", test_patient_exists, "Verify patients are loaded")
    tester.run_test("conditions_linked", test_conditions_linked, "Verify conditions reference patients")
    tester.run_test("observations_valid", test_observation_values, "Verify observations have values")

    # Get results
    summary = tester.get_summary()
    print(f"\nTest Results:")
    print(f"  Total: {summary['total']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Pass Rate: {summary['pass_rate']:.0%}")

    for result in tester.get_results():
        status_icon = "✓" if result["status"] == "passed" else "✗"
        print(f"  {status_icon} {result['name']}: {result['status']}")
    print()


def sandbox_environment_example():
    """Using the complete sandbox environment."""
    print("=== Complete Sandbox Environment ===\n")

    # Create sandbox with reproducible seed
    sandbox = FHIRSandbox(seed=789)

    # Generate and load test data
    bundle = sandbox.generate_test_data(num_patients=10, load_to_server=True)
    print(f"Generated {len(bundle.entry)} resources")

    # Use the integrated server
    patients = sandbox.server.search("Patient", {})
    print(f"Server has {len(patients.entry)} patients")

    # Validate generated data
    for entry in bundle.entry[:3]:  # Validate first 3
        result = sandbox.validator.validate(entry.resource)
        res_type = entry.resource.resource_type
        res_id = entry.resource.id
        status = "VALID" if result.is_valid else f"INVALID ({result.error_count} errors)"
        print(f"  {res_type}/{res_id}: {status}")

    # Run workflow tests
    def test_all_patients_have_data(t: WorkflowTester) -> bool:
        patients = t.server.search("Patient", {})
        for entry in patients.entry:
            patient_id = entry.resource.id
            conditions = t.server.search("Condition", {"patient": f"Patient/{patient_id}"})
            observations = t.server.search("Observation", {"patient": f"Patient/{patient_id}"})
            if len(conditions.entry) == 0 and len(observations.entry) == 0:
                return False
        return True

    sandbox.tester.run_test(
        "all_patients_have_data",
        test_all_patients_have_data,
        "All patients have associated resources"
    )

    print(f"\nWorkflow test: {sandbox.tester.get_summary()}")

    # Reset sandbox
    sandbox.reset()
    print("\nSandbox reset - server cleared")
    print()


def convenience_functions_example():
    """Using convenience functions for quick testing."""
    print("=== Convenience Functions ===\n")

    # Quick patient creation
    patient = create_test_patient(gender="male", age_range=(25, 35))
    print(f"Test patient: {patient.name[0].given[0]} {patient.name[0].family}")

    # Quick bundle creation
    bundle = create_test_bundle(
        num_patients=2,
        conditions_per_patient=1,
        observations_per_patient=2
    )
    print(f"Test bundle: {len(bundle.entry)} resources")

    # Quick synthetic data
    data = generate_synthetic_data(num_patients=5, seed=999)
    print(f"Synthetic data: {len(data.entry)} resources")
    print()


def main():
    """Run all sandbox examples."""
    print("\n" + "=" * 60)
    print("FHIR Sandbox Testing Examples")
    print("=" * 60 + "\n")

    synthetic_data_generation_example()
    patient_bundle_generation()
    population_bundle_generation()
    mock_server_example()
    transaction_bundle_example()
    workflow_testing_example()
    sandbox_environment_example()
    convenience_functions_example()

    print("=" * 60)
    print("Sandbox examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
