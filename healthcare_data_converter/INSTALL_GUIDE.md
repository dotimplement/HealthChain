# Healthcare Data Converter - Installation Guide

## Step 1: Install from Source

```bash
# Navigate to healthcare_data_converter directory
cd /care-chain/healthcare_data_converter

# Activate virtual environment (if using venv)
source ../venv/bin/activate

# Install the package
pip install -e .
```

## Step 2: Verify Installation

```bash
python -c "from healthcare_data_converter import HealthcareDataConverter; print('✓ Installation verified: OK')"
```

## Step 3: Test Basic Conversion

### CDA to FHIR Example

Create a test file `test_cda_to_fhir.py`:

```python
from healthcare_data_converter import HealthcareDataConverter

# Create converter
converter = HealthcareDataConverter()

# Read CDA document (you'll need a sample CDA file)
with open("patient.xml") as f:
    cda_xml = f.read()

# Convert to FHIR
fhir_resources, warnings = converter.cda_to_fhir(cda_xml)

# Process results
for resource in fhir_resources:
    print(f"{resource['resourceType']}: {resource.get('id')}")

# Print warnings if any
if warnings:
    print("\nWarnings:")
    for warning in warnings:
        print(f"  - {warning}")
```

### FHIR to CDA Example

Create a test file `test_fhir_to_cda.py`:

```python
from healthcare_data_converter import HealthcareDataConverter, DocumentType

converter = HealthcareDataConverter()

# FHIR Bundle
fhir_bundle = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [
        {
            "resource": {
                "resourceType": "Condition",
                "id": "1",
                "code": {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": "44054006",
                        "display": "Type 2 diabetes"
                    }]
                }
            }
        }
    ]
}

# Convert to CDA
cda_xml, warnings = converter.fhir_to_cda(
    fhir_bundle,
    document_type=DocumentType.CCD
)

# Save result
with open("patient_ccd.xml", "w") as f:
    f.write(cda_xml)

print("✓ Conversion complete: patient_ccd.xml")
```

## Step 4: Test CLI Commands

### Basic Conversion

```bash
# CDA to FHIR
healthcare-converter convert -i patient.xml -s cda -t fhir -o patient.json

# FHIR to CDA
healthcare-converter convert -i bundle.json -s fhir -t cda -d ccd -o patient.xml
```

### With Options

```bash
# Pretty print JSON
healthcare-converter convert -i input.xml -s cda -t fhir --pretty

# Strict validation
healthcare-converter convert -i input.json -s fhir -t cda --validation strict

# Different document type
healthcare-converter convert -i bundle.json -s fhir -t cda -d discharge_summary
```

## Step 5: Start API Server

```bash
healthcare-converter serve --host 0.0.0.0 --port 8000
```

Then access:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Troubleshooting

### If installation fails:

1. **Make sure you're in the virtual environment:**
   ```bash
   source ../venv/bin/activate
   ```

2. **Install dependencies manually:**
   ```bash
   pip install fhir.resources pydantic fastapi uvicorn httpx python-liquid xmltodict lxml pyyaml
   ```

3. **Install healthchain first:**
   ```bash
   cd ..
   pip install -e .
   cd healthcare_data_converter
   pip install -e .
   ```

### Verify CLI is installed:

```bash
which healthcare-converter
healthcare-converter --help
```

## Next Steps

- See `GUIDELINES.md` for detailed usage
- See `TECHNICAL_BUSINESS_SUMMARY.md` for architecture
- Check `examples/` directory for more examples

### uninstall 
 ```
 rm .pyenv/versions/3.10.3/bin/healthcare-converter && \
rm ~/.pyenv/shims/healthcare-converter && \
pyenv rehash && \
echo "✓ Đã xóa healthcare-converter" && \
which healthcare-converter || echo "✓ Command không còn tồn tại"
 ```

