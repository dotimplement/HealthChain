#!/bin/bash
# Healthcare Data Format Converter - Quick Start Script
# ======================================================
#
# This script helps you get started with the Healthcare Data Format Converter.

set -e

echo "Healthcare Data Format Converter - Quick Start"
echo "==============================================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo ""

# Install dependencies if needed
echo "Checking dependencies..."
pip install -q fhir.resources pydantic fastapi uvicorn httpx python-liquid xmltodict

echo ""
echo "Running quick test..."
echo "---------------------"

python3 << 'EOF'
import sys
sys.path.insert(0, '.')

from healthcare_data_converter import HealthcareDataConverter, DocumentType

# Create converter
converter = HealthcareDataConverter()

# Test FHIR to CDA conversion
print("Testing FHIR -> CDA conversion...")

fhir_condition = {
    "resourceType": "Condition",
    "id": "test-condition",
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
    "subject": {"reference": "Patient/1"}
}

try:
    cda_xml, warnings = converter.fhir_to_cda(
        fhir_condition,
        document_type=DocumentType.CCD
    )
    print(f"  Generated CDA document ({len(cda_xml)} bytes)")
    if warnings:
        print(f"  Warnings: {len(warnings)}")
    print("  Status: SUCCESS")
except Exception as e:
    print(f"  Status: FAILED - {e}")

print()

# Get capabilities
print("Converter Capabilities:")
capabilities = converter.get_capabilities()
print(f"  Supported conversions: {len(capabilities.supported_conversions)}")
print(f"  Supported document types: {len(capabilities.supported_document_types)}")
print(f"  Supported FHIR resources: {len(capabilities.supported_fhir_resources)}")

print()
print("Quick start completed successfully!")
EOF

echo ""
echo "==============================================="
echo "Next Steps:"
echo "  1. Start the API server:"
echo "     python -m healthcare_data_converter.cli serve"
echo ""
echo "  2. Run the examples:"
echo "     python healthcare_data_converter/examples/basic_conversion.py"
echo ""
echo "  3. Read the documentation:"
echo "     - GUIDELINES.md - User guide"
echo "     - TECHNICAL_BUSINESS_SUMMARY.md - Technical overview"
echo "==============================================="
