"""
API Usage Examples for Healthcare Data Converter

This script demonstrates how to interact with the Healthcare Data
Format Converter API using both the Python client and raw HTTP requests.
"""

import json
import httpx

# API base URL (adjust if running on different host/port)
API_BASE = "http://localhost:8000"


async def example_health_check():
    """Check API health status."""
    print("=" * 60)
    print("Health Check")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/health")
        data = response.json()

        print(f"Status: {data['status']}")
        print(f"Version: {data['version']}")
        print(f"Supported Formats: {', '.join(data['supported_formats'])}")


async def example_get_capabilities():
    """Get API capabilities."""
    print("\n" + "=" * 60)
    print("Get Capabilities")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/api/v1/capabilities")
        data = response.json()

        print("Supported Conversions:")
        for conv in data["supported_conversions"]:
            print(f"  {conv['source']} -> {conv['target']}")

        print(f"\nSupported FHIR Resources: {len(data['supported_fhir_resources'])}")
        print(f"Max Batch Size: {data['max_batch_size']}")


async def example_convert_fhir_to_cda():
    """Convert FHIR to CDA via API."""
    print("\n" + "=" * 60)
    print("Convert FHIR to CDA")
    print("=" * 60)

    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-1",
                    "code": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "44054006",
                                "display": "Type 2 diabetes mellitus",
                            }
                        ]
                    },
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                "code": "active",
                            }
                        ]
                    },
                    "subject": {"reference": "Patient/patient-1"},
                }
            }
        ],
    }

    request_body = {
        "data": fhir_bundle,
        "source_format": "fhir",
        "target_format": "cda",
        "document_type": "ccd",
        "validation_level": "warn",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/convert",
            json=request_body,
            timeout=30.0,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
            print(f"Conversion ID: {data['metadata']['conversion_id']}")
            print(f"Processing Time: {data['metadata']['processing_time_ms']}ms")
            print(f"Resources: {data['metadata']['resource_count']}")

            if data.get("warnings"):
                print(f"Warnings: {len(data['warnings'])}")

            # Show first 200 chars of CDA
            if data.get("data"):
                print(f"\nCDA Output (preview):")
                print(data["data"][:200] + "...")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)


async def example_convert_cda_to_fhir():
    """Convert CDA to FHIR via API."""
    print("\n" + "=" * 60)
    print("Convert CDA to FHIR")
    print("=" * 60)

    cda_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <ClinicalDocument xmlns="urn:hl7-org:v3">
        <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
        <templateId root="2.16.840.1.113883.10.20.22.1.1"/>
        <id root="2.16.840.1.113883.19.5.99999.1"/>
        <code code="34133-9" codeSystem="2.16.840.1.113883.6.1"/>
        <effectiveTime value="20240115"/>
        <confidentialityCode code="N" codeSystem="2.16.840.1.113883.5.25"/>
        <recordTarget>
            <patientRole>
                <id extension="12345"/>
            </patientRole>
        </recordTarget>
        <component>
            <structuredBody>
                <component>
                    <section>
                        <templateId root="2.16.840.1.113883.10.20.22.2.5"/>
                        <code code="11450-4" codeSystem="2.16.840.1.113883.6.1"/>
                        <title>Problems</title>
                    </section>
                </component>
            </structuredBody>
        </component>
    </ClinicalDocument>
    """

    request_body = {
        "data": cda_xml,
        "source_format": "cda",
        "target_format": "fhir",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/convert",
            json=request_body,
            timeout=30.0,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
            print(f"Resources: {data['metadata']['resource_count']}")

            if data.get("data"):
                print(f"\nFHIR Resources:")
                for resource in data["data"][:3]:  # Show first 3
                    print(f"  - {resource.get('resourceType')}: {resource.get('id')}")
        else:
            print(f"Error: {response.status_code}")


async def example_batch_convert():
    """Batch convert multiple documents via API."""
    print("\n" + "=" * 60)
    print("Batch Conversion")
    print("=" * 60)

    # Multiple conditions to convert
    documents = [
        {
            "data": {
                "resourceType": "Condition",
                "id": f"condition-{i}",
                "code": {
                    "coding": [{"system": "http://snomed.info/sct", "code": code}]
                },
                "subject": {"reference": "Patient/1"},
            },
            "source_format": "fhir",
            "target_format": "cda",
            "document_type": "ccd",
        }
        for i, code in enumerate(["44054006", "38341003", "195967001"])
    ]

    request_body = {
        "documents": documents,
        "parallel": True,
        "stop_on_error": False,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/convert/batch",
            json=request_body,
            timeout=60.0,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Total: {data['total']}")
            print(f"Successful: {data['successful']}")
            print(f"Failed: {data['failed']}")
            print(f"Processing Time: {data['processing_time_ms']}ms")
        else:
            print(f"Error: {response.status_code}")


async def example_validate():
    """Validate documents via API."""
    print("\n" + "=" * 60)
    print("Validation")
    print("=" * 60)

    # Validate FHIR
    fhir_data = {
        "resourceType": "Condition",
        "id": "test",
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": "12345"}]},
        "subject": {"reference": "Patient/1"},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/api/v1/validate/fhir",
            json=fhir_data,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"FHIR Valid: {data['valid']}")
            if data.get("messages"):
                for msg in data["messages"]:
                    print(f"  - {msg}")


def curl_examples():
    """Print curl command examples for testing the API."""
    print("\n" + "=" * 60)
    print("CURL Examples")
    print("=" * 60)

    print("""
# Health Check
curl -X GET "http://localhost:8000/health"

# Get Capabilities
curl -X GET "http://localhost:8000/api/v1/capabilities"

# Convert FHIR to CDA
curl -X POST "http://localhost:8000/api/v1/convert" \\
  -H "Content-Type: application/json" \\
  -d '{
    "data": {
      "resourceType": "Condition",
      "id": "test",
      "code": {"coding": [{"system": "http://snomed.info/sct", "code": "44054006"}]},
      "subject": {"reference": "Patient/1"}
    },
    "source_format": "fhir",
    "target_format": "cda",
    "document_type": "ccd"
  }'

# List Formats
curl -X GET "http://localhost:8000/api/v1/formats"

# List Document Types
curl -X GET "http://localhost:8000/api/v1/document-types"
""")


async def main():
    """Run all API examples."""
    import asyncio

    print("Healthcare Data Converter API Examples")
    print("Make sure the API server is running: healthcare-converter serve")
    print()

    try:
        await example_health_check()
        await example_get_capabilities()
        await example_convert_fhir_to_cda()
        await example_convert_cda_to_fhir()
        await example_batch_convert()
        await example_validate()
    except httpx.ConnectError:
        print("\nError: Could not connect to API server.")
        print("Start the server with: healthcare-converter serve")

    curl_examples()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
