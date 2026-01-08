# Healthcare Data Format Converter
## User Guidelines

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Command Line Interface](#command-line-interface)
4. [Python SDK](#python-sdk)
5. [REST API](#rest-api)
6. [Configuration](#configuration)
7. [Data Formats](#data-formats)
8. [Conversion Examples](#conversion-examples)
9. [Validation](#validation)
10. [Error Handling](#error-handling)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Install from Source

```bash
# Clone the repository
git clone https://github.com/dotimplement/HealthChain.git
cd HealthChain

# Install dependencies
pip install -e .

# Verify installation
python -c "from healthcare_data_converter import HealthcareDataConverter; print('OK')"
```

### Install Dependencies Only

```bash
pip install fhir.resources pydantic fastapi uvicorn httpx python-liquid xmltodict
```

---

## Quick Start

### Convert CDA to FHIR (Python)

```python
from healthcare_data_converter import HealthcareDataConverter

# Create converter
converter = HealthcareDataConverter()

# Read CDA document
with open("patient.xml") as f:
    cda_xml = f.read()

# Convert to FHIR
fhir_resources, warnings = converter.cda_to_fhir(cda_xml)

# Process results
for resource in fhir_resources:
    print(f"{resource['resourceType']}: {resource.get('id')}")
```

### Convert FHIR to CDA (Python)

```python
from healthcare_data_converter import HealthcareDataConverter, DocumentType

converter = HealthcareDataConverter()

# FHIR Bundle
fhir_bundle = {
    "resourceType": "Bundle",
    "entry": [
        {"resource": {"resourceType": "Condition", "id": "1", ...}}
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
```

### Convert via CLI

```bash
# CDA to FHIR
healthcare-converter convert -i patient.xml -s cda -t fhir -o patient.json

# FHIR to CDA
healthcare-converter convert -i bundle.json -s fhir -t cda -d ccd -o patient.xml
```

### Start API Server

```bash
healthcare-converter serve --host 0.0.0.0 --port 8000
```

---

## Command Line Interface

### Commands Overview

| Command | Description |
|---------|-------------|
| `convert` | Convert a single file |
| `batch` | Batch convert multiple files |
| `validate` | Validate document format |
| `serve` | Start the API server |
| `info` | Show capabilities |

### Convert Command

```bash
healthcare-converter convert [OPTIONS]

Options:
  -i, --input PATH        Input file path or '-' for stdin (required)
  -o, --output PATH       Output file path or '-' for stdout (default: stdout)
  -s, --source FORMAT     Source format: fhir, cda, hl7v2 (required)
  -t, --target FORMAT     Target format: fhir, cda (required)
  -d, --document-type     CDA document type (default: ccd)
  --validation LEVEL      Validation: strict, warn, ignore (default: warn)
  --no-narrative          Exclude narrative from CDA output
  --pretty                Pretty-print JSON output
  -v, --verbose           Enable verbose output
```

**Examples:**

```bash
# Basic conversion
healthcare-converter convert -i input.xml -s cda -t fhir -o output.json

# With pretty printing
healthcare-converter convert -i input.xml -s cda -t fhir --pretty

# Pipe from stdin
cat patient.xml | healthcare-converter convert -i - -s cda -t fhir

# Strict validation
healthcare-converter convert -i input.json -s fhir -t cda --validation strict

# Different document type
healthcare-converter convert -i bundle.json -s fhir -t cda -d discharge_summary
```

### Batch Command

```bash
healthcare-converter batch [OPTIONS]

Options:
  -i, --input-dir PATH    Input directory (required)
  -o, --output-dir PATH   Output directory (required)
  -s, --source FORMAT     Source format (required)
  -t, --target FORMAT     Target format (required)
  -p, --pattern GLOB      File pattern to match (default: *)
  -d, --document-type     CDA document type (default: ccd)
  -v, --verbose           Enable verbose output
```

**Examples:**

```bash
# Convert all XML files in a directory
healthcare-converter batch -i ./cda_docs -o ./fhir_output -s cda -t fhir -p "*.xml"

# Convert specific pattern
healthcare-converter batch -i ./input -o ./output -s fhir -t cda -p "patient_*.json"
```

### Validate Command

```bash
healthcare-converter validate [OPTIONS]

Options:
  -i, --input PATH    Input file path (required)
  -f, --format TYPE   Format to validate: cda, fhir (required)
  -v, --verbose       Enable verbose output
```

**Examples:**

```bash
# Validate CDA
healthcare-converter validate -i document.xml -f cda

# Validate FHIR
healthcare-converter validate -i bundle.json -f fhir
```

### Serve Command

```bash
healthcare-converter serve [OPTIONS]

Options:
  --host HOST         Host to bind to (default: 0.0.0.0)
  --port PORT         Port to bind to (default: 8000)
  --reload            Enable auto-reload for development
  --log-level LEVEL   Logging level: debug, info, warning, error
```

**Examples:**

```bash
# Start production server
healthcare-converter serve --host 0.0.0.0 --port 8000

# Development mode with auto-reload
healthcare-converter serve --reload --log-level debug

# Custom port
healthcare-converter serve --port 3000
```

### Info Command

```bash
healthcare-converter info [OPTIONS]

Options:
  --json    Output as JSON
```

---

## Python SDK

### Initialization

```python
from healthcare_data_converter import (
    HealthcareDataConverter,
    ConversionRequest,
    ConversionFormat,
    DocumentType,
    ValidationLevel,
)

# Default configuration
converter = HealthcareDataConverter()

# Custom configuration
converter = HealthcareDataConverter(
    config_dir="./custom_configs",
    template_dir="./custom_templates",
    validation_level=ValidationLevel.STRICT,
    default_document_type=DocumentType.DISCHARGE_SUMMARY,
)
```

### Simple Conversion Methods

```python
# CDA to FHIR
fhir_resources, warnings = converter.cda_to_fhir(cda_xml)

# FHIR to CDA
cda_xml, warnings = converter.fhir_to_cda(
    fhir_data,  # Bundle, list, or single resource
    document_type=DocumentType.CCD,
    include_narrative=True,
)
```

### Request-Based Conversion

```python
from healthcare_data_converter import ConversionRequest, ConversionFormat

request = ConversionRequest(
    data=input_data,
    source_format=ConversionFormat.CDA,
    target_format=ConversionFormat.FHIR,
    validation_level=ValidationLevel.WARN,
)

response = converter.convert(request)

if response.status == ConversionStatus.SUCCESS:
    output = response.data
    print(f"Converted {response.metadata.resource_count} resources")
else:
    for error in response.errors:
        print(f"Error: {error}")
```

### Validation

```python
# Validate CDA
is_valid, messages = converter.validate_cda(cda_xml)

# Validate FHIR
is_valid, messages = converter.validate_fhir(fhir_data)
```

### Get Capabilities

```python
capabilities = converter.get_capabilities()

print(f"Supported conversions: {capabilities.supported_conversions}")
print(f"Supported resources: {capabilities.supported_fhir_resources}")
print(f"Max batch size: {capabilities.max_batch_size}")
```

---

## REST API

### Base URL

```
http://localhost:8000
```

### Endpoints

#### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "supported_formats": ["fhir", "cda", "hl7v2"],
  "supported_document_types": ["ccd", "discharge_summary", ...],
  "timestamp": "2024-01-15T12:00:00Z"
}
```

#### Get Capabilities

```http
GET /api/v1/capabilities
```

**Response:**
```json
{
  "supported_conversions": [
    {"source": "cda", "target": "fhir"},
    {"source": "fhir", "target": "cda"},
    {"source": "hl7v2", "target": "fhir"}
  ],
  "supported_document_types": ["ccd", "discharge_summary", ...],
  "supported_fhir_resources": ["Condition", "MedicationStatement", ...],
  "max_batch_size": 100,
  "validation_levels": ["strict", "warn", "ignore"]
}
```

#### Convert

```http
POST /api/v1/convert
Content-Type: application/json

{
  "data": "<ClinicalDocument>...</ClinicalDocument>",
  "source_format": "cda",
  "target_format": "fhir",
  "document_type": "ccd",
  "validation_level": "warn",
  "include_narrative": true
}
```

**Response:**
```json
{
  "status": "success",
  "data": [
    {"resourceType": "Condition", "id": "condition-1", ...}
  ],
  "metadata": {
    "conversion_id": "conv-abc123",
    "source_format": "cda",
    "target_format": "fhir",
    "processing_time_ms": 45.2,
    "resource_count": 5,
    "warning_count": 0,
    "error_count": 0
  },
  "resources": [
    {"resource_type": "Condition", "resource_id": "condition-1", "status": "converted"}
  ],
  "warnings": [],
  "errors": []
}
```

#### Batch Convert

```http
POST /api/v1/convert/batch
Content-Type: application/json

{
  "documents": [
    {"data": "...", "source_format": "fhir", "target_format": "cda"},
    {"data": "...", "source_format": "fhir", "target_format": "cda"}
  ],
  "parallel": true,
  "stop_on_error": false
}
```

**Response:**
```json
{
  "total": 2,
  "successful": 2,
  "failed": 0,
  "results": [...],
  "processing_time_ms": 120.5
}
```

#### Validate CDA

```http
POST /api/v1/validate/cda
Content-Type: text/plain

<ClinicalDocument>...</ClinicalDocument>
```

#### Validate FHIR

```http
POST /api/v1/validate/fhir
Content-Type: application/json

{"resourceType": "Condition", ...}
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Convert FHIR to CDA
curl -X POST http://localhost:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"resourceType": "Condition", "id": "1"},
    "source_format": "fhir",
    "target_format": "cda",
    "document_type": "ccd"
  }'

# Get capabilities
curl http://localhost:8000/api/v1/capabilities
```

---

## Configuration

### Configuration File Location

Default: `healthcare_data_converter/configs/settings.yaml`

### Key Configuration Options

```yaml
# Application settings
app:
  name: "Healthcare Data Converter"
  version: "1.0.0"

# Conversion defaults
conversion:
  validation_level: warn          # strict, warn, ignore
  default_document_type: ccd      # CDA document type
  include_narrative: true         # Include human-readable text
  preserve_ids: true              # Keep original resource IDs
  max_batch_size: 100             # Maximum batch size
  timeout: 300                    # Processing timeout (seconds)

# Server settings
server:
  host: "0.0.0.0"
  port: 8000
  cors:
    enabled: true
    origins: ["*"]

# Performance tuning
performance:
  worker_threads: 4
  template_caching: true
  max_concurrent: 10
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CONVERTER_HOST` | API server host | 0.0.0.0 |
| `CONVERTER_PORT` | API server port | 8000 |
| `CONVERTER_LOG_LEVEL` | Logging level | INFO |
| `CONVERTER_CONFIG_DIR` | Custom config directory | None |

---

## Data Formats

### FHIR R4

The converter supports FHIR R4 resources in JSON format.

**Supported input formats:**
- FHIR Bundle
- Array of resources
- Single resource
- JSON string

**Example Bundle:**
```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [
    {
      "resource": {
        "resourceType": "Condition",
        "id": "condition-1",
        "code": {
          "coding": [{
            "system": "http://snomed.info/sct",
            "code": "44054006",
            "display": "Type 2 diabetes mellitus"
          }]
        },
        "clinicalStatus": {
          "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
            "code": "active"
          }]
        },
        "subject": {"reference": "Patient/patient-1"}
      }
    }
  ]
}
```

### CDA R2

The converter supports CDA R2 documents in XML format.

**Supported document types:**
- CCD (Continuity of Care Document)
- Discharge Summary
- Progress Note
- Consultation Note
- History and Physical
- Operative Note
- Procedure Note
- Referral Note

**Example CDA structure:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
  <templateId root="2.16.840.1.113883.10.20.22.1.1"/>
  <id root="2.16.840.1.113883.19.5.99999.1"/>
  <code code="34133-9" codeSystem="2.16.840.1.113883.6.1"/>
  ...
  <component>
    <structuredBody>
      <component>
        <section>
          <!-- Section content -->
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>
```

---

## Conversion Examples

### Example 1: Patient Summary (CDA → FHIR)

```python
from healthcare_data_converter import HealthcareDataConverter

converter = HealthcareDataConverter()

# CDA document with patient info and conditions
cda_xml = """<?xml version="1.0"?>
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <!-- ... document structure ... -->
</ClinicalDocument>
"""

fhir_resources, warnings = converter.cda_to_fhir(cda_xml)

# Extract specific resource types
conditions = [r for r in fhir_resources if r['resourceType'] == 'Condition']
medications = [r for r in fhir_resources if r['resourceType'] == 'MedicationStatement']
```

### Example 2: Discharge Summary (FHIR → CDA)

```python
from healthcare_data_converter import HealthcareDataConverter, DocumentType

converter = HealthcareDataConverter()

# Discharge summary resources
discharge_bundle = {
    "resourceType": "Bundle",
    "entry": [
        # Patient, Encounter, Conditions, Medications, etc.
    ]
}

cda_xml, warnings = converter.fhir_to_cda(
    discharge_bundle,
    document_type=DocumentType.DISCHARGE_SUMMARY,
)
```

### Example 3: Batch Processing

```python
import json
from pathlib import Path
from healthcare_data_converter import HealthcareDataConverter, ConversionRequest, ConversionFormat

converter = HealthcareDataConverter()
input_dir = Path("./cda_documents")
output_dir = Path("./fhir_output")
output_dir.mkdir(exist_ok=True)

for cda_file in input_dir.glob("*.xml"):
    cda_xml = cda_file.read_text()

    request = ConversionRequest(
        data=cda_xml,
        source_format=ConversionFormat.CDA,
        target_format=ConversionFormat.FHIR,
    )

    response = converter.convert(request)

    if response.status.value == "success":
        output_file = output_dir / f"{cda_file.stem}.json"
        output_file.write_text(json.dumps(response.data, indent=2))
        print(f"Converted: {cda_file.name}")
    else:
        print(f"Failed: {cda_file.name} - {response.errors}")
```

---

## Validation

### Validation Levels

| Level | Behavior |
|-------|----------|
| **STRICT** | Fails on any validation error. Use for production data. |
| **WARN** | Logs warnings but continues processing. Use for development. |
| **IGNORE** | Skips validation entirely. Use for testing. |

### Validation Examples

```python
from healthcare_data_converter import HealthcareDataConverter, ValidationLevel

# Strict validation
converter = HealthcareDataConverter(validation_level=ValidationLevel.STRICT)

# Explicit validation
is_valid, messages = converter.validate_cda(cda_xml)
if not is_valid:
    for msg in messages:
        print(f"Validation error: {msg}")
```

---

## Error Handling

### Response Status Values

| Status | Description |
|--------|-------------|
| `success` | All resources converted without issues |
| `partial` | Conversion completed with warnings |
| `failed` | Conversion failed with errors |

### Error Response Structure

```json
{
  "status": "failed",
  "data": null,
  "metadata": {...},
  "warnings": [],
  "errors": [
    "Invalid FHIR resource: missing required field 'subject'",
    "CDA section template ID not recognized"
  ]
}
```

### Handling Errors in Code

```python
response = converter.convert(request)

if response.status == ConversionStatus.FAILED:
    for error in response.errors:
        logger.error(f"Conversion error: {error}")
    raise ConversionError(response.errors)

elif response.status == ConversionStatus.PARTIAL:
    for warning in response.warnings:
        logger.warning(f"Conversion warning: {warning}")
    # Continue with partial data

# Process successful conversion
output_data = response.data
```

---

## Best Practices

### 1. Input Validation

Always validate input before conversion:

```python
# Validate first
is_valid, messages = converter.validate_cda(cda_xml)
if not is_valid:
    handle_validation_errors(messages)
    return

# Then convert
response = converter.convert(request)
```

### 2. Error Logging

Implement comprehensive logging:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

response = converter.convert(request)

logger.info(f"Conversion {response.metadata.conversion_id}: "
            f"{response.metadata.resource_count} resources in "
            f"{response.metadata.processing_time_ms}ms")

for warning in response.warnings:
    logger.warning(f"Conversion warning: {warning}")
```

### 3. Batch Processing

For large volumes, use batch conversion:

```python
from healthcare_data_converter.models import BatchConversionRequest

batch_request = BatchConversionRequest(
    documents=conversion_requests,
    parallel=True,           # Enable parallel processing
    stop_on_error=False,     # Continue on individual failures
)

# Use API for batch
response = await client.post("/api/v1/convert/batch", json=batch_request)
```

### 4. Resource Cleanup

Handle resources properly:

```python
try:
    response = converter.convert(request)
    # Process response
finally:
    # Cleanup if needed
    pass
```

### 5. Configuration Management

Use environment-specific configurations:

```python
import os

env = os.getenv("ENVIRONMENT", "development")

if env == "production":
    validation = ValidationLevel.STRICT
else:
    validation = ValidationLevel.WARN

converter = HealthcareDataConverter(validation_level=validation)
```

---

## Troubleshooting

### Common Issues

#### 1. "Template not found" Error

**Cause:** Custom template directory not configured correctly.

**Solution:**
```python
converter = HealthcareDataConverter(
    template_dir="/path/to/templates"
)
```

#### 2. "Invalid CDA structure" Error

**Cause:** CDA document doesn't match expected schema.

**Solution:**
- Validate the CDA document first
- Check templateId matches supported document types
- Ensure required sections are present

#### 3. "FHIR resource validation failed" Error

**Cause:** FHIR resource missing required fields.

**Solution:**
```python
# Check required fields before conversion
resource = {
    "resourceType": "Condition",
    "subject": {"reference": "Patient/1"},  # Required
    "code": {...},  # Required
}
```

#### 4. Slow Conversion Performance

**Cause:** Large documents or inefficient configuration.

**Solution:**
- Enable template caching in configuration
- Increase worker threads for batch processing
- Use parallel processing for batch operations

#### 5. Memory Issues with Large Batches

**Cause:** Processing too many documents simultaneously.

**Solution:**
- Reduce batch size
- Process in chunks:
```python
chunk_size = 20
for i in range(0, len(documents), chunk_size):
    chunk = documents[i:i+chunk_size]
    process_batch(chunk)
```

### Debug Mode

Enable debug logging:

```bash
healthcare-converter serve --log-level debug
```

Or in Python:

```python
import logging
logging.getLogger("healthcare_data_converter").setLevel(logging.DEBUG)
```

### Getting Help

- Check the examples in `examples/` directory
- Review the technical summary in `TECHNICAL_BUSINESS_SUMMARY.md`
- Report issues on GitHub
- Join the HealthChain Discord community

---

## Appendix

### Supported Code Systems

| FHIR URL | CDA OID | Name |
|----------|---------|------|
| http://snomed.info/sct | 2.16.840.1.113883.6.96 | SNOMED CT |
| http://loinc.org | 2.16.840.1.113883.6.1 | LOINC |
| http://www.nlm.nih.gov/research/umls/rxnorm | 2.16.840.1.113883.6.88 | RxNorm |
| http://hl7.org/fhir/sid/icd-10-cm | 2.16.840.1.113883.6.90 | ICD-10-CM |
| http://hl7.org/fhir/sid/ndc | 2.16.840.1.113883.6.69 | NDC |

### CDA Section LOINC Codes

| Section | LOINC Code | FHIR Resource |
|---------|------------|---------------|
| Problems | 11450-4 | Condition |
| Medications | 10160-0 | MedicationStatement |
| Allergies | 48765-2 | AllergyIntolerance |
| Vital Signs | 8716-3 | Observation |
| Procedures | 47519-4 | Procedure |
| Immunizations | 11369-6 | Immunization |
| Results | 30954-2 | DiagnosticReport |
| Encounters | 46240-8 | Encounter |
