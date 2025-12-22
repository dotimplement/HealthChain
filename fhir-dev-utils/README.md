# FHIR Development Utilities

Accelerate healthcare application development with type-safe FHIR resource creation, validation helpers, and sandbox environments for testing clinical workflows.

## Features

| Feature | Description |
|---------|-------------|
| **Type-Safe Builders** | Fluent builder pattern for all common FHIR resources |
| **Validation Helpers** | Schema validation, reference checks, custom rules |
| **Bundle Operations** | Create, merge, analyze, and manipulate FHIR bundles |
| **Sandbox Environment** | Mock FHIR server and synthetic data generation |
| **Format Converters** | FHIR to/from dict, DataFrame, flat structures |

## Quick Start

```python
from fhir_utils import ResourceFactory, validate_resource, BundleBuilder
from sandbox import FHIRSandbox

# Create a patient with type-safe builder
patient = ResourceFactory.patient() \
    .with_name("Smith", given=["John"]) \
    .with_birth_date("1985-03-15") \
    .with_gender("male") \
    .with_mrn("MRN123456") \
    .build()

# Validate the resource
result = validate_resource(patient)
print(f"Valid: {result.is_valid}")

# Create a sandbox for testing
sandbox = FHIRSandbox(seed=42)
test_data = sandbox.generate_test_data(num_patients=10)
```

## Installation

```bash
# From the HealthChain project root
cd fhir-dev-utils
pip install -e ..  # Install HealthChain
```

### Dependencies

- Python 3.9+
- fhir.resources >= 8.0.0
- pydantic >= 2.0.0, < 2.11.0
- pandas (optional, for DataFrame operations)

## Usage Guide

### Resource Creation

Create FHIR resources using the fluent builder pattern:

```python
from fhir_utils import ResourceFactory

# Patient
patient = ResourceFactory.patient() \
    .with_id("patient-001") \
    .with_name("Doe", given=["Jane"], prefix=["Dr."]) \
    .with_birth_date("1990-05-20") \
    .with_gender("female") \
    .with_mrn("MRN789012") \
    .with_contact(phone="555-1234", email="jane@hospital.org") \
    .with_address(city="Boston", state="MA", postal_code="02101") \
    .active() \
    .build()

# Condition (SNOMED CT)
condition = ResourceFactory.condition() \
    .for_patient(patient.id) \
    .with_snomed("73211009", "Diabetes mellitus") \
    .with_clinical_status("active") \
    .with_verification_status("confirmed") \
    .with_severity("moderate") \
    .build()

# Observation (LOINC)
observation = ResourceFactory.observation() \
    .for_patient(patient.id) \
    .with_loinc("2339-0", "Glucose") \
    .with_value_quantity(95, "mg/dL") \
    .with_status("final") \
    .with_interpretation("N") \
    .with_reference_range(low=70, high=100, unit="mg/dL") \
    .build()

# Medication Statement (RxNorm)
medication = ResourceFactory.medication_statement() \
    .for_patient(patient.id) \
    .with_rxnorm("197361", "Metformin 500 MG") \
    .with_status("active") \
    .with_dosage("Take 500mg twice daily with meals") \
    .build()

# Allergy Intolerance
allergy = ResourceFactory.allergy_intolerance() \
    .for_patient(patient.id) \
    .with_code("91936005", display="Penicillin allergy") \
    .with_clinical_status("active") \
    .with_criticality("high") \
    .with_reaction("271807003", "Skin rash", severity="moderate") \
    .build()
```

### Validation

Validate resources with comprehensive error reporting:

```python
from fhir_utils import FHIRValidator, validate_resource, validate_bundle

# Basic validation
result = validate_resource(patient)
if not result.is_valid:
    for error in result.errors:
        print(f"Error at {error.path}: {error.message}")

# Strict mode (warnings become errors)
strict_result = validate_resource(patient, strict=True)

# Custom validation rules
validator = FHIRValidator()

def require_mrn(resource, result):
    if not getattr(resource, "identifier", None):
        result.add_error("Patient must have MRN", path="identifier")

validator.add_custom_rule("Patient", require_mrn)
result = validator.validate(patient)

# Validate entire bundle
bundle_result = validate_bundle(bundle, validate_entry_resources=True)
```

### Bundle Operations

Create and manipulate FHIR bundles:

```python
from fhir_utils import BundleBuilder, BundleAnalyzer, merge_bundles_smart

# Create collection bundle
bundle = BundleBuilder() \
    .with_id("my-bundle") \
    .with_timestamp() \
    .as_collection() \
    .add(patient) \
    .add(condition) \
    .add(observation) \
    .build()

# Create transaction bundle
tx_bundle = BundleBuilder() \
    .as_transaction() \
    .add(patient, method="POST") \
    .add(condition, method="POST", url="Condition") \
    .build()

# Analyze bundle contents
analyzer = BundleAnalyzer(bundle)
print(f"Total: {analyzer.total}")
print(f"Types: {analyzer.resource_types}")
print(f"Counts: {analyzer.get_resource_counts()}")

# Get specific resources
patients = analyzer.get_resources("Patient")
patient_conditions = analyzer.get_resources_for_patient("Patient/patient-001", "Condition")

# Merge bundles
merged = merge_bundles_smart([bundle1, bundle2], deduplicate=True)
```

### Sandbox Environment

Test workflows without connecting to real EHR systems:

```python
from sandbox import FHIRSandbox, MockFHIRServer, SyntheticDataGenerator

# Complete sandbox environment
sandbox = FHIRSandbox(seed=42)

# Generate test data
test_bundle = sandbox.generate_test_data(num_patients=10)

# Use mock server
patients = sandbox.server.search("Patient", {})
conditions = sandbox.server.search("Condition", {"patient": "Patient/123"})

# Validate generated data
for entry in test_bundle.entry:
    result = sandbox.validator.validate(entry.resource)

# Reset sandbox
sandbox.reset()
```

### Synthetic Data Generation

Generate realistic test data:

```python
from sandbox import SyntheticDataGenerator, create_test_bundle

# Generator with seed for reproducibility
generator = SyntheticDataGenerator(seed=123)

# Generate single patient
patient = generator.generate_patient(gender="female", age_range=(30, 50))

# Generate patient with all resources
patient_bundle = generator.generate_patient_bundle(
    num_conditions=3,
    num_observations=5,
    num_medications=2,
    num_allergies=1
)

# Generate population
population = generator.generate_population_bundle(
    num_patients=100,
    resources_per_patient={
        "conditions": 2,
        "observations": 4,
        "medications": 1,
        "allergies": 1,
    }
)

# Quick convenience function
quick_bundle = create_test_bundle(num_patients=5)
```

### Mock FHIR Server

Test FHIR operations locally:

```python
from sandbox import MockFHIRServer

server = MockFHIRServer()

# CRUD operations
created = server.create(patient)
retrieved = server.read("Patient", patient.id)
updated = server.update(modified_patient)
deleted = server.delete("Patient", patient.id)

# Search
results = server.search("Condition", {
    "patient": "Patient/123",
    "_id": "condition-456"
})

# Execute transaction bundle
response = server.execute_bundle(transaction_bundle)

# Load test data
server.load_bundle(test_bundle)

# Check history
history = server.get_history()
```

### Workflow Testing

Structured testing for clinical workflows:

```python
from sandbox import WorkflowTester, create_test_bundle

tester = WorkflowTester()

# Setup test data
tester.setup(create_test_bundle(num_patients=5))

# Define tests
def test_patients_loaded(t):
    results = t.server.search("Patient", {})
    return len(results.entry) == 5

def test_conditions_valid(t):
    for entry in t.server.search("Condition", {}).entry:
        result = t.validate_resource(entry.resource)
        if not result.is_valid:
            return False
    return True

# Run tests
tester.run_test("patients_loaded", test_patients_loaded)
tester.run_test("conditions_valid", test_conditions_valid)

# Get results
summary = tester.get_summary()
print(f"Pass rate: {summary['pass_rate']:.0%}")
```

## CLI Usage

```bash
# Run demo
python app.py demo

# Demo specific component
python app.py demo --component resources
python app.py demo --component validation
python app.py demo --component sandbox

# Generate synthetic data
python app.py generate --patients 10 --seed 42 --output test_data.json

# Validate FHIR JSON
cat resource.json | python app.py validate
```

## Project Structure

```
fhir-dev-utils/
├── app.py                    # Main application entry point
├── fhir_utils/
│   ├── __init__.py          # Public API exports
│   ├── resource_factory.py  # Type-safe resource builders
│   ├── validators.py        # Validation utilities
│   ├── bundle_tools.py      # Bundle manipulation
│   └── converters.py        # Format converters
├── sandbox/
│   ├── __init__.py          # Sandbox exports
│   └── test_environment.py  # Mock server & generators
├── examples/
│   ├── basic_resource_creation.py
│   ├── validation_example.py
│   └── sandbox_testing.py
├── tests/
│   └── test_fhir_utils.py   # Test suite
├── README.md
└── SUMMARY.md
```

## Supported Resource Types

| Resource | Builder | Code Systems |
|----------|---------|--------------|
| Patient | `PatientBuilder` | - |
| Condition | `ConditionBuilder` | SNOMED CT, ICD-10 |
| Observation | `ObservationBuilder` | LOINC |
| MedicationStatement | `MedicationStatementBuilder` | RxNorm |
| AllergyIntolerance | `AllergyIntoleranceBuilder` | SNOMED CT |
| DocumentReference | `DocumentReferenceBuilder` | LOINC |
| Bundle | `BundleBuilder` | - |

## Examples

See the `examples/` directory for detailed usage:

- `basic_resource_creation.py` - Creating all resource types
- `validation_example.py` - Validation patterns and custom rules
- `sandbox_testing.py` - Mock server and workflow testing

## Running Tests

```bash
cd fhir-dev-utils
pytest tests/ -v
```

## Integration with HealthChain

This utility integrates with the HealthChain framework:

```python
from healthchain.gateway import FHIRGateway
from fhir_utils import ResourceFactory, validate_resource

# Create validated resources for gateway
patient = ResourceFactory.patient() \
    .with_name("Smith", given=["John"]) \
    .build()

result = validate_resource(patient)
if result.is_valid:
    gateway = FHIRGateway()
    gateway.add_source("local", "http://localhost:8080/fhir")
    gateway.create(patient, source="local")
```

## Contributing

1. Follow the HealthChain coding style (Ruff, type hints)
2. Add tests for new functionality
3. Update documentation as needed
4. Use synthetic data only - no PHI

## License

Part of the HealthChain project - see main repository for license details.
