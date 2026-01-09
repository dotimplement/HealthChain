"""
FHIR Development Sandbox Test Environment

Provides mock servers, synthetic data generation, and workflow testing
utilities for developing healthcare applications without real EHR systems.
"""

import uuid
import random
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Union, Callable
from collections import defaultdict

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance

import sys
sys.path.insert(0, "..")
from fhir_utils.resource_factory import (
    ResourceFactory,
    PatientBuilder,
    ConditionBuilder,
    ObservationBuilder,
    MedicationStatementBuilder,
    AllergyIntoleranceBuilder,
)
from fhir_utils.bundle_tools import BundleBuilder, BundleAnalyzer
from fhir_utils.validators import FHIRValidator, ValidationResult


def _generate_id(prefix: str = "test") -> str:
    """Generate a unique test ID."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class SyntheticDataGenerator:
    """
    Generator for synthetic FHIR test data.

    Creates realistic but fake healthcare data for testing purposes.
    """

    # Sample data for generation
    FIRST_NAMES_MALE = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph"]
    FIRST_NAMES_FEMALE = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]

    # Common conditions with SNOMED codes
    CONDITIONS = [
        ("73211009", "Diabetes mellitus"),
        ("38341003", "Hypertension"),
        ("195967001", "Asthma"),
        ("84114007", "Heart failure"),
        ("13645005", "Chronic obstructive pulmonary disease"),
        ("44054006", "Type 2 diabetes mellitus"),
        ("40930008", "Hypothyroidism"),
        ("35489007", "Depression"),
    ]

    # Common observations with LOINC codes
    OBSERVATIONS = [
        ("8480-6", "Systolic blood pressure", "mm[Hg]", 90, 180),
        ("8462-4", "Diastolic blood pressure", "mm[Hg]", 60, 120),
        ("8867-4", "Heart rate", "/min", 50, 120),
        ("8310-5", "Body temperature", "Cel", 36.0, 39.0),
        ("29463-7", "Body weight", "kg", 40, 150),
        ("8302-2", "Body height", "cm", 140, 200),
        ("2339-0", "Glucose", "mg/dL", 70, 200),
        ("2093-3", "Total cholesterol", "mg/dL", 120, 280),
    ]

    # Common medications with RxNorm codes
    MEDICATIONS = [
        ("197361", "Metformin 500 MG Oral Tablet"),
        ("866924", "Lisinopril 10 MG Oral Tablet"),
        ("197319", "Aspirin 81 MG Oral Tablet"),
        ("314076", "Atorvastatin 20 MG Oral Tablet"),
        ("311995", "Omeprazole 20 MG Delayed Release Oral Capsule"),
        ("966571", "Amlodipine 5 MG Oral Tablet"),
    ]

    # Common allergies with SNOMED codes
    ALLERGIES = [
        ("91936005", "Penicillin allergy"),
        ("91935009", "Peanut allergy"),
        ("294505008", "Sulfonamide allergy"),
        ("300916003", "Latex allergy"),
        ("418038007", "Propensity to adverse reactions to substance"),
    ]

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize generator with optional seed for reproducibility.

        Args:
            seed: Random seed for reproducible generation
        """
        if seed is not None:
            random.seed(seed)
        self._id_counter = 0

    def _next_id(self, prefix: str = "gen") -> str:
        """Generate sequential IDs."""
        self._id_counter += 1
        return f"{prefix}-{self._id_counter:04d}"

    def generate_patient(
        self,
        patient_id: Optional[str] = None,
        gender: Optional[str] = None,
        age_range: tuple = (18, 85)
    ) -> Patient:
        """
        Generate a synthetic patient.

        Args:
            patient_id: Custom ID or auto-generate
            gender: 'male', 'female', or random
            age_range: Tuple of (min_age, max_age)

        Returns:
            Patient resource
        """
        if gender is None:
            gender = random.choice(["male", "female"])

        if gender == "male":
            first_name = random.choice(self.FIRST_NAMES_MALE)
        else:
            first_name = random.choice(self.FIRST_NAMES_FEMALE)

        last_name = random.choice(self.LAST_NAMES)
        age = random.randint(*age_range)
        birth_date = date.today() - timedelta(days=age * 365 + random.randint(0, 365))

        builder = ResourceFactory.patient()
        if patient_id:
            builder.with_id(patient_id)
        else:
            builder.with_id(self._next_id("patient"))

        return (builder
            .with_name(last_name, given=[first_name])
            .with_gender(gender)
            .with_birth_date(birth_date)
            .with_mrn(f"MRN{random.randint(100000, 999999)}")
            .active()
            .build())

    def generate_condition(
        self,
        patient_id: str,
        condition_id: Optional[str] = None,
        specific_condition: Optional[tuple] = None
    ) -> Condition:
        """
        Generate a synthetic condition.

        Args:
            patient_id: Patient reference ID
            condition_id: Custom ID or auto-generate
            specific_condition: (code, display) or random

        Returns:
            Condition resource
        """
        if specific_condition:
            code, display = specific_condition
        else:
            code, display = random.choice(self.CONDITIONS)

        onset_days_ago = random.randint(30, 1825)  # 1 month to 5 years
        onset_date = date.today() - timedelta(days=onset_days_ago)

        builder = ResourceFactory.condition()
        if condition_id:
            builder.with_id(condition_id)
        else:
            builder.with_id(self._next_id("condition"))

        return (builder
            .for_patient(patient_id)
            .with_snomed(code, display)
            .with_clinical_status("active")
            .with_verification_status("confirmed")
            .with_category("encounter-diagnosis")
            .with_onset(onset_date)
            .build())

    def generate_observation(
        self,
        patient_id: str,
        observation_id: Optional[str] = None,
        specific_observation: Optional[tuple] = None
    ) -> Observation:
        """
        Generate a synthetic observation.

        Args:
            patient_id: Patient reference ID
            observation_id: Custom ID or auto-generate
            specific_observation: (code, display, unit, min, max) or random

        Returns:
            Observation resource
        """
        if specific_observation:
            code, display, unit, min_val, max_val = specific_observation
        else:
            code, display, unit, min_val, max_val = random.choice(self.OBSERVATIONS)

        value = round(random.uniform(min_val, max_val), 1)
        effective_datetime = datetime.now() - timedelta(hours=random.randint(0, 48))

        builder = ResourceFactory.observation()
        if observation_id:
            builder.with_id(observation_id)
        else:
            builder.with_id(self._next_id("observation"))

        return (builder
            .for_patient(patient_id)
            .with_loinc(code, display)
            .with_value_quantity(value, unit)
            .with_status("final")
            .with_category("vital-signs")
            .with_effective_datetime(effective_datetime)
            .build())

    def generate_medication_statement(
        self,
        patient_id: str,
        medication_id: Optional[str] = None,
        specific_medication: Optional[tuple] = None
    ) -> MedicationStatement:
        """
        Generate a synthetic medication statement.

        Args:
            patient_id: Patient reference ID
            medication_id: Custom ID or auto-generate
            specific_medication: (code, display) or random

        Returns:
            MedicationStatement resource
        """
        if specific_medication:
            code, display = specific_medication
        else:
            code, display = random.choice(self.MEDICATIONS)

        start_days_ago = random.randint(7, 365)
        start_date = date.today() - timedelta(days=start_days_ago)

        builder = ResourceFactory.medication_statement()
        if medication_id:
            builder.with_id(medication_id)
        else:
            builder.with_id(self._next_id("medication"))

        return (builder
            .for_patient(patient_id)
            .with_rxnorm(code, display)
            .with_status("active")
            .with_effective_period(start_date)
            .with_dosage("Take as directed")
            .build())

    def generate_allergy(
        self,
        patient_id: str,
        allergy_id: Optional[str] = None,
        specific_allergy: Optional[tuple] = None
    ) -> AllergyIntolerance:
        """
        Generate a synthetic allergy.

        Args:
            patient_id: Patient reference ID
            allergy_id: Custom ID or auto-generate
            specific_allergy: (code, display) or random

        Returns:
            AllergyIntolerance resource
        """
        if specific_allergy:
            code, display = specific_allergy
        else:
            code, display = random.choice(self.ALLERGIES)

        builder = ResourceFactory.allergy_intolerance()
        if allergy_id:
            builder.with_id(allergy_id)
        else:
            builder.with_id(self._next_id("allergy"))

        return (builder
            .for_patient(patient_id)
            .with_code(code, "http://snomed.info/sct", display)
            .with_clinical_status("active")
            .with_verification_status("confirmed")
            .with_type("allergy")
            .with_category("medication")
            .with_criticality(random.choice(["low", "high"]))
            .build())

    def generate_patient_bundle(
        self,
        num_conditions: int = 3,
        num_observations: int = 5,
        num_medications: int = 2,
        num_allergies: int = 1
    ) -> Bundle:
        """
        Generate a complete patient bundle with associated resources.

        Args:
            num_conditions: Number of conditions to generate
            num_observations: Number of observations to generate
            num_medications: Number of medications to generate
            num_allergies: Number of allergies to generate

        Returns:
            Bundle with patient and related resources
        """
        patient = self.generate_patient()
        patient_id = patient.id

        builder = BundleBuilder().as_collection()
        builder.add(patient)

        for _ in range(num_conditions):
            builder.add(self.generate_condition(patient_id))

        for _ in range(num_observations):
            builder.add(self.generate_observation(patient_id))

        for _ in range(num_medications):
            builder.add(self.generate_medication_statement(patient_id))

        for _ in range(num_allergies):
            builder.add(self.generate_allergy(patient_id))

        return builder.build()

    def generate_population_bundle(
        self,
        num_patients: int = 10,
        resources_per_patient: Dict[str, int] = None
    ) -> Bundle:
        """
        Generate a bundle with multiple patients and their resources.

        Args:
            num_patients: Number of patients to generate
            resources_per_patient: Dict with resource counts

        Returns:
            Bundle with multiple patients
        """
        if resources_per_patient is None:
            resources_per_patient = {
                "conditions": 2,
                "observations": 4,
                "medications": 2,
                "allergies": 1,
            }

        builder = BundleBuilder().as_collection()

        for _ in range(num_patients):
            patient = self.generate_patient()
            patient_id = patient.id
            builder.add(patient)

            for _ in range(resources_per_patient.get("conditions", 0)):
                builder.add(self.generate_condition(patient_id))

            for _ in range(resources_per_patient.get("observations", 0)):
                builder.add(self.generate_observation(patient_id))

            for _ in range(resources_per_patient.get("medications", 0)):
                builder.add(self.generate_medication_statement(patient_id))

            for _ in range(resources_per_patient.get("allergies", 0)):
                builder.add(self.generate_allergy(patient_id))

        return builder.build()


class MockFHIRServer:
    """
    Mock FHIR server for testing without real EHR connectivity.

    Simulates basic FHIR REST API operations.
    """

    def __init__(self):
        """Initialize mock server."""
        self._resources: Dict[str, Dict[str, Resource]] = defaultdict(dict)
        self._history: List[Dict[str, Any]] = []

    def create(self, resource: Union[Resource, Dict[str, Any]]) -> Resource:
        """
        Create a resource (POST).

        Args:
            resource: FHIR resource to create

        Returns:
            Created resource with assigned ID
        """
        if isinstance(resource, dict):
            from fhir.resources import get_fhir_model_class
            res_type = resource.get("resourceType")
            model_class = get_fhir_model_class(res_type)
            resource = model_class(**resource)

        res_type = resource.resource_type
        res_id = getattr(resource, "id", None) or _generate_id(res_type.lower())

        # Assign ID if not present
        if not getattr(resource, "id", None):
            resource.id = res_id

        self._resources[res_type][res_id] = resource
        self._history.append({
            "operation": "create",
            "resourceType": res_type,
            "id": res_id,
            "timestamp": datetime.now().isoformat()
        })

        return resource

    def read(
        self,
        resource_type: str,
        resource_id: str
    ) -> Optional[Resource]:
        """
        Read a resource (GET).

        Args:
            resource_type: Resource type name
            resource_id: Resource ID

        Returns:
            Resource if found, None otherwise
        """
        return self._resources.get(resource_type, {}).get(resource_id)

    def update(self, resource: Union[Resource, Dict[str, Any]]) -> Resource:
        """
        Update a resource (PUT).

        Args:
            resource: Resource with ID to update

        Returns:
            Updated resource
        """
        if isinstance(resource, dict):
            from fhir.resources import get_fhir_model_class
            res_type = resource.get("resourceType")
            model_class = get_fhir_model_class(res_type)
            resource = model_class(**resource)

        res_type = resource.resource_type
        res_id = resource.id

        if not res_id:
            raise ValueError("Resource must have an ID for update")

        self._resources[res_type][res_id] = resource
        self._history.append({
            "operation": "update",
            "resourceType": res_type,
            "id": res_id,
            "timestamp": datetime.now().isoformat()
        })

        return resource

    def delete(self, resource_type: str, resource_id: str) -> bool:
        """
        Delete a resource (DELETE).

        Args:
            resource_type: Resource type name
            resource_id: Resource ID

        Returns:
            True if deleted, False if not found
        """
        if resource_id in self._resources.get(resource_type, {}):
            del self._resources[resource_type][resource_id]
            self._history.append({
                "operation": "delete",
                "resourceType": resource_type,
                "id": resource_id,
                "timestamp": datetime.now().isoformat()
            })
            return True
        return False

    def search(
        self,
        resource_type: str,
        params: Optional[Dict[str, str]] = None
    ) -> Bundle:
        """
        Search for resources.

        Args:
            resource_type: Resource type to search
            params: Search parameters

        Returns:
            Bundle of matching resources
        """
        resources = list(self._resources.get(resource_type, {}).values())

        # Simple filtering
        if params:
            filtered = []
            for resource in resources:
                match = True
                for key, value in params.items():
                    # Handle patient/subject references
                    if key in ("patient", "subject"):
                        ref = getattr(resource, "subject", None) or getattr(resource, "patient", None)
                        if not ref or value not in (ref.reference or ""):
                            match = False
                            break
                    # Handle ID
                    elif key == "_id":
                        if resource.id != value:
                            match = False
                            break
                if match:
                    filtered.append(resource)
            resources = filtered

        builder = BundleBuilder().as_searchset()
        for resource in resources:
            builder.add(resource)

        return builder.build()

    def execute_bundle(
        self,
        bundle: Union[Bundle, Dict[str, Any]]
    ) -> Bundle:
        """
        Execute a transaction/batch bundle.

        Args:
            bundle: Transaction or batch bundle

        Returns:
            Response bundle
        """
        if isinstance(bundle, dict):
            bundle = Bundle(**bundle)

        response_builder = BundleBuilder()
        if bundle.type == "transaction":
            response_builder.as_transaction()
        else:
            response_builder.as_batch()

        for entry in bundle.entry or []:
            resource = entry.resource
            request = entry.request

            if not request:
                continue

            method = request.method.upper() if request.method else "GET"

            try:
                if method == "POST":
                    created = self.create(resource)
                    response_builder.add(created)
                elif method == "PUT":
                    updated = self.update(resource)
                    response_builder.add(updated)
                elif method == "DELETE":
                    parts = request.url.split("/")
                    if len(parts) >= 2:
                        self.delete(parts[0], parts[1])
            except Exception:
                continue

        return response_builder.build()

    def get_history(self) -> List[Dict[str, Any]]:
        """Get operation history."""
        return list(self._history)

    def clear(self) -> None:
        """Clear all resources and history."""
        self._resources.clear()
        self._history.clear()

    def load_bundle(self, bundle: Union[Bundle, Dict[str, Any]]) -> int:
        """
        Load resources from a bundle into the server.

        Args:
            bundle: Bundle to load

        Returns:
            Number of resources loaded
        """
        if isinstance(bundle, dict):
            bundle = Bundle(**bundle)

        count = 0
        for entry in bundle.entry or []:
            if entry.resource:
                self.create(entry.resource)
                count += 1

        return count


class WorkflowTester:
    """
    Utility for testing clinical workflows with validation.

    Provides structured testing of FHIR-based clinical workflows.
    """

    def __init__(self, mock_server: Optional[MockFHIRServer] = None):
        """
        Initialize workflow tester.

        Args:
            mock_server: Optional mock server to use
        """
        self.server = mock_server or MockFHIRServer()
        self.validator = FHIRValidator()
        self._test_results: List[Dict[str, Any]] = []

    def setup(self, bundle: Union[Bundle, Dict[str, Any]]) -> int:
        """
        Set up test data.

        Args:
            bundle: Bundle of test data to load

        Returns:
            Number of resources loaded
        """
        return self.server.load_bundle(bundle)

    def run_test(
        self,
        name: str,
        test_fn: Callable[["WorkflowTester"], bool],
        description: str = ""
    ) -> bool:
        """
        Run a single test.

        Args:
            name: Test name
            test_fn: Test function taking tester and returning pass/fail
            description: Optional description

        Returns:
            True if test passed
        """
        start_time = datetime.now()

        try:
            result = test_fn(self)
            status = "passed" if result else "failed"
            error = None
        except Exception as e:
            result = False
            status = "error"
            error = str(e)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self._test_results.append({
            "name": name,
            "description": description,
            "status": status,
            "duration": duration,
            "error": error,
            "timestamp": start_time.isoformat()
        })

        return result

    def validate_resource(self, resource: Union[Resource, Dict[str, Any]]) -> ValidationResult:
        """
        Validate a resource.

        Args:
            resource: Resource to validate

        Returns:
            ValidationResult
        """
        return self.validator.validate(resource)

    def assert_resource_exists(
        self,
        resource_type: str,
        resource_id: str
    ) -> bool:
        """
        Assert that a resource exists.

        Args:
            resource_type: Resource type
            resource_id: Resource ID

        Returns:
            True if exists
        """
        resource = self.server.read(resource_type, resource_id)
        return resource is not None

    def assert_search_count(
        self,
        resource_type: str,
        params: Dict[str, str],
        expected_count: int
    ) -> bool:
        """
        Assert search returns expected number of results.

        Args:
            resource_type: Resource type to search
            params: Search parameters
            expected_count: Expected number of results

        Returns:
            True if count matches
        """
        bundle = self.server.search(resource_type, params)
        actual_count = len(bundle.entry or [])
        return actual_count == expected_count

    def get_results(self) -> List[Dict[str, Any]]:
        """Get all test results."""
        return list(self._test_results)

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary."""
        passed = sum(1 for r in self._test_results if r["status"] == "passed")
        failed = sum(1 for r in self._test_results if r["status"] == "failed")
        errors = sum(1 for r in self._test_results if r["status"] == "error")

        return {
            "total": len(self._test_results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": passed / len(self._test_results) if self._test_results else 0
        }


class FHIRSandbox:
    """
    Complete sandbox environment for FHIR development.

    Combines mock server, data generation, and workflow testing.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize sandbox.

        Args:
            seed: Random seed for reproducible data generation
        """
        self.generator = SyntheticDataGenerator(seed=seed)
        self.server = MockFHIRServer()
        self.tester = WorkflowTester(mock_server=self.server)
        self.validator = FHIRValidator()

    def generate_test_data(
        self,
        num_patients: int = 5,
        load_to_server: bool = True
    ) -> Bundle:
        """
        Generate test data.

        Args:
            num_patients: Number of patients
            load_to_server: Whether to load into mock server

        Returns:
            Generated bundle
        """
        bundle = self.generator.generate_population_bundle(num_patients)

        if load_to_server:
            self.server.load_bundle(bundle)

        return bundle

    def reset(self) -> None:
        """Reset sandbox to clean state."""
        self.server.clear()
        self.tester._test_results.clear()


# Convenience functions

def create_test_patient(**kwargs) -> Patient:
    """Create a test patient with optional customization."""
    generator = SyntheticDataGenerator()
    return generator.generate_patient(**kwargs)


def create_test_bundle(
    num_patients: int = 1,
    conditions_per_patient: int = 2,
    observations_per_patient: int = 3
) -> Bundle:
    """Create a test bundle with customizable contents."""
    generator = SyntheticDataGenerator()
    return generator.generate_population_bundle(
        num_patients=num_patients,
        resources_per_patient={
            "conditions": conditions_per_patient,
            "observations": observations_per_patient,
            "medications": 1,
            "allergies": 1,
        }
    )


def generate_synthetic_data(
    num_patients: int = 10,
    seed: Optional[int] = None
) -> Bundle:
    """Generate synthetic FHIR data for testing."""
    generator = SyntheticDataGenerator(seed=seed)
    return generator.generate_population_bundle(num_patients)
