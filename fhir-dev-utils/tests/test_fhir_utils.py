"""
Tests for FHIR Development Utilities

Comprehensive test suite for resource creation, validation,
bundle operations, and sandbox functionality.
"""

import pytest
import sys
sys.path.insert(0, "..")

from fhir_utils import (
    ResourceFactory,
    PatientBuilder,
    ConditionBuilder,
    ObservationBuilder,
    FHIRValidator,
    ValidationResult,
    validate_resource,
    validate_bundle,
    check_required_fields,
    BundleBuilder,
    BundleAnalyzer,
    create_transaction_bundle,
    create_collection_bundle,
    merge_bundles_smart,
)
from sandbox import (
    FHIRSandbox,
    MockFHIRServer,
    SyntheticDataGenerator,
    WorkflowTester,
    create_test_patient,
    create_test_bundle,
)


class TestResourceFactory:
    """Tests for ResourceFactory and builders."""

    def test_patient_builder_basic(self):
        """Test basic patient creation."""
        patient = ResourceFactory.patient() \
            .with_name("Smith", given=["John"]) \
            .with_gender("male") \
            .build()

        assert patient.resourceType == "Patient"
        assert patient.name[0].family == "Smith"
        assert patient.name[0].given[0] == "John"
        assert patient.gender == "male"

    def test_patient_builder_full(self):
        """Test patient with all fields."""
        patient = ResourceFactory.patient() \
            .with_id("test-patient-001") \
            .with_name("Doe", given=["Jane", "Marie"], prefix=["Dr."]) \
            .with_birth_date("1990-05-15") \
            .with_gender("female") \
            .with_mrn("MRN123456", system="http://hospital.org") \
            .with_contact(phone="555-1234", email="jane@example.com") \
            .with_address(city="Boston", state="MA") \
            .active() \
            .build()

        assert patient.id == "test-patient-001"
        assert patient.birthDate.isoformat() == "1990-05-15"
        assert patient.active is True
        assert len(patient.identifier) == 1
        assert len(patient.telecom) == 2

    def test_condition_builder(self):
        """Test condition creation."""
        condition = ResourceFactory.condition() \
            .for_patient("patient-123") \
            .with_snomed("73211009", "Diabetes mellitus") \
            .with_clinical_status("active") \
            .with_verification_status("confirmed") \
            .build()

        assert condition.resourceType == "Condition"
        assert condition.subject.reference == "Patient/patient-123"
        assert condition.code.coding[0].code == "73211009"
        assert condition.clinicalStatus.coding[0].code == "active"

    def test_observation_builder(self):
        """Test observation creation."""
        observation = ResourceFactory.observation() \
            .for_patient("patient-123") \
            .with_loinc("2339-0", "Glucose") \
            .with_value_quantity(95.5, "mg/dL") \
            .with_status("final") \
            .with_interpretation("N") \
            .build()

        assert observation.resourceType == "Observation"
        assert observation.valueQuantity.value == 95.5
        assert observation.valueQuantity.unit == "mg/dL"
        assert observation.interpretation[0].coding[0].code == "N"

    def test_medication_statement_builder(self):
        """Test medication statement creation."""
        med = ResourceFactory.medication_statement() \
            .for_patient("patient-123") \
            .with_rxnorm("197361", "Metformin 500 MG") \
            .with_status("active") \
            .with_dosage("Take twice daily") \
            .build()

        assert med.resourceType == "MedicationStatement"
        assert med.status == "active"
        assert med.dosage[0].text == "Take twice daily"

    def test_allergy_builder(self):
        """Test allergy intolerance creation."""
        allergy = ResourceFactory.allergy_intolerance() \
            .for_patient("patient-123") \
            .with_code("91936005", display="Penicillin allergy") \
            .with_clinical_status("active") \
            .with_criticality("high") \
            .build()

        assert allergy.resourceType == "AllergyIntolerance"
        assert allergy.criticality == "high"


class TestValidation:
    """Tests for validation utilities."""

    def test_validate_valid_resource(self):
        """Test validation of valid resource."""
        patient = ResourceFactory.patient() \
            .with_name("Test", given=["User"]) \
            .with_gender("male") \
            .build()

        result = validate_resource(patient)
        assert result.is_valid is True
        assert result.error_count == 0

    def test_validate_invalid_resource(self):
        """Test validation of invalid resource."""
        invalid_dict = {
            "resourceType": "Condition",
            # Missing required 'subject' field
        }

        result = validate_resource(invalid_dict)
        assert result.is_valid is False
        assert result.error_count > 0

    def test_strict_validation(self):
        """Test strict validation mode."""
        # Minimal patient without recommended fields
        patient = ResourceFactory.patient().build()

        # Normal mode: warnings only
        normal_result = validate_resource(patient, strict=False)
        assert normal_result.warning_count > 0

        # Strict mode: warnings become errors
        strict_result = validate_resource(patient, strict=True)
        assert strict_result.is_valid is False

    def test_custom_validation_rule(self):
        """Test custom validation rules."""
        validator = FHIRValidator()

        def require_gender(resource, result):
            if not getattr(resource, "gender", None):
                result.add_error("Gender is required", path="gender")

        validator.add_custom_rule("Patient", require_gender)

        patient_no_gender = ResourceFactory.patient() \
            .with_name("Test", given=["User"]) \
            .build()

        result = validator.validate(patient_no_gender)
        assert result.is_valid is False
        assert any("Gender" in e.message for e in result.errors)

    def test_check_required_fields(self):
        """Test required fields check."""
        condition = ResourceFactory.condition() \
            .for_patient("patient-123") \
            .with_snomed("73211009", "Diabetes") \
            .with_clinical_status("active") \
            .build()

        result = check_required_fields(condition, ["id", "subject", "code"])
        assert result.is_valid is True

        result = check_required_fields(condition, ["nonexistent"])
        assert result.is_valid is False


class TestBundleTools:
    """Tests for bundle manipulation tools."""

    def test_bundle_builder_collection(self):
        """Test collection bundle creation."""
        patient = ResourceFactory.patient() \
            .with_name("Test") \
            .build()

        bundle = BundleBuilder() \
            .as_collection() \
            .add(patient) \
            .build()

        assert bundle.type == "collection"
        assert len(bundle.entry) == 1

    def test_bundle_builder_transaction(self):
        """Test transaction bundle creation."""
        patient = ResourceFactory.patient() \
            .with_id("tx-patient") \
            .with_name("Test") \
            .build()

        bundle = BundleBuilder() \
            .as_transaction() \
            .add(patient, method="POST") \
            .build()

        assert bundle.type == "transaction"
        assert bundle.entry[0].request.method == "POST"

    def test_bundle_analyzer(self):
        """Test bundle analysis."""
        patient = ResourceFactory.patient() \
            .with_id("analyzer-test") \
            .with_name("Test") \
            .build()

        condition = ResourceFactory.condition() \
            .for_patient("analyzer-test") \
            .with_snomed("73211009", "Diabetes") \
            .build()

        bundle = BundleBuilder() \
            .as_collection() \
            .add(patient) \
            .add(condition) \
            .build()

        analyzer = BundleAnalyzer(bundle)

        assert analyzer.total == 2
        assert "Patient" in analyzer.resource_types
        assert "Condition" in analyzer.resource_types
        assert len(analyzer.get_resources("Patient")) == 1

    def test_merge_bundles(self):
        """Test bundle merging."""
        bundle1 = create_collection_bundle([
            ResourceFactory.patient().with_id("p1").with_name("One").build()
        ])

        bundle2 = create_collection_bundle([
            ResourceFactory.patient().with_id("p2").with_name("Two").build()
        ])

        merged = merge_bundles_smart([bundle1, bundle2])
        assert len(merged.entry) == 2


class TestSandbox:
    """Tests for sandbox environment."""

    def test_synthetic_data_generator(self):
        """Test synthetic data generation."""
        generator = SyntheticDataGenerator(seed=42)

        patient = generator.generate_patient()
        assert patient.resourceType == "Patient"
        assert patient.name is not None

        condition = generator.generate_condition(patient.id)
        assert condition.resourceType == "Condition"
        assert patient.id in condition.subject.reference

    def test_mock_server_crud(self):
        """Test mock server CRUD operations."""
        server = MockFHIRServer()

        # Create
        patient = ResourceFactory.patient() \
            .with_id("crud-test") \
            .with_name("CRUD", given=["Test"]) \
            .build()

        created = server.create(patient)
        assert created.id == "crud-test"

        # Read
        retrieved = server.read("Patient", "crud-test")
        assert retrieved is not None
        assert retrieved.name[0].family == "CRUD"

        # Update
        patient.active = True
        updated = server.update(patient)
        assert updated.active is True

        # Delete
        deleted = server.delete("Patient", "crud-test")
        assert deleted is True
        assert server.read("Patient", "crud-test") is None

    def test_mock_server_search(self):
        """Test mock server search."""
        server = MockFHIRServer()

        # Create patient and conditions
        patient = ResourceFactory.patient() \
            .with_id("search-patient") \
            .with_name("Search") \
            .build()
        server.create(patient)

        for i in range(3):
            condition = ResourceFactory.condition() \
                .for_patient("search-patient") \
                .with_snomed(f"1234{i}", f"Condition {i}") \
                .build()
            server.create(condition)

        # Search
        results = server.search("Condition", {"patient": "Patient/search-patient"})
        assert len(results.entry) == 3

    def test_fhir_sandbox(self):
        """Test complete sandbox environment."""
        sandbox = FHIRSandbox(seed=123)

        bundle = sandbox.generate_test_data(num_patients=3)
        assert len(bundle.entry) > 3  # Patient + resources

        patients = sandbox.server.search("Patient", {})
        assert len(patients.entry) == 3

    def test_workflow_tester(self):
        """Test workflow testing utilities."""
        tester = WorkflowTester()

        bundle = create_test_bundle(num_patients=2)
        tester.setup(bundle)

        def test_fn(t):
            return len(t.server.search("Patient", {}).entry) == 2

        result = tester.run_test("patient_count", test_fn)
        assert result is True

        summary = tester.get_summary()
        assert summary["passed"] == 1


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_test_patient(self):
        """Test create_test_patient function."""
        patient = create_test_patient(gender="female")
        assert patient.resourceType == "Patient"
        assert patient.gender == "female"

    def test_create_test_bundle(self):
        """Test create_test_bundle function."""
        bundle = create_test_bundle(
            num_patients=2,
            conditions_per_patient=1,
            observations_per_patient=2
        )

        analyzer = BundleAnalyzer(bundle)
        assert len(analyzer.get_resources("Patient")) == 2
        assert len(analyzer.get_resources("Condition")) == 2
        assert len(analyzer.get_resources("Observation")) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
