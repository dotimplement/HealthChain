"""
Basic Healthcare Data Conversion Examples

This script demonstrates the core functionality of the Healthcare Data
Format Converter application for converting between FHIR and CDA formats.
"""

import json

from healthcare_data_converter import (
    HealthcareDataConverter,
    ConversionRequest,
    ConversionFormat,
    DocumentType,
    ValidationLevel,
)


def example_cda_to_fhir():
    """Convert a CDA document to FHIR resources."""
    print("=" * 60)
    print("Example 1: CDA to FHIR Conversion")
    print("=" * 60)

    # Sample CDA document (simplified for demonstration)
    cda_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <ClinicalDocument xmlns="urn:hl7-org:v3">
        <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
        <templateId root="2.16.840.1.113883.10.20.22.1.1"/>
        <id root="2.16.840.1.113883.19.5.99999.1"/>
        <code code="34133-9" codeSystem="2.16.840.1.113883.6.1" displayName="Summarization of Episode Note"/>
        <title>Patient Health Summary</title>
        <effectiveTime value="20240115120000"/>
        <confidentialityCode code="N" codeSystem="2.16.840.1.113883.5.25"/>
        <recordTarget>
            <patientRole>
                <id root="2.16.840.1.113883.4.1" extension="123-45-6789"/>
                <patient>
                    <name>
                        <given>John</given>
                        <family>Smith</family>
                    </name>
                    <administrativeGenderCode code="M" codeSystem="2.16.840.1.113883.5.1"/>
                    <birthTime value="19800315"/>
                </patient>
            </patientRole>
        </recordTarget>
        <component>
            <structuredBody>
                <component>
                    <section>
                        <templateId root="2.16.840.1.113883.10.20.22.2.5"/>
                        <code code="11450-4" codeSystem="2.16.840.1.113883.6.1" displayName="Problem List"/>
                        <title>Problems</title>
                        <entry>
                            <act classCode="ACT" moodCode="EVN">
                                <entryRelationship typeCode="SUBJ">
                                    <observation classCode="OBS" moodCode="EVN">
                                        <code code="55607006" codeSystem="2.16.840.1.113883.6.96"
                                              displayName="Problem"/>
                                        <statusCode code="completed"/>
                                        <effectiveTime>
                                            <low value="20230101"/>
                                        </effectiveTime>
                                        <value xsi:type="CD" code="44054006"
                                               codeSystem="2.16.840.1.113883.6.96"
                                               displayName="Type 2 Diabetes Mellitus"
                                               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
                                    </observation>
                                </entryRelationship>
                            </act>
                        </entry>
                    </section>
                </component>
            </structuredBody>
        </component>
    </ClinicalDocument>
    """

    # Create converter
    converter = HealthcareDataConverter(
        validation_level=ValidationLevel.WARN
    )

    # Convert CDA to FHIR
    fhir_resources, warnings = converter.cda_to_fhir(cda_xml)

    print(f"\nConverted {len(fhir_resources)} FHIR resources:")
    for resource in fhir_resources:
        print(f"  - {resource.get('resourceType')}: {resource.get('id', 'N/A')}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")

    print("\nFHIR Output (first resource):")
    if fhir_resources:
        print(json.dumps(fhir_resources[0], indent=2))

    return fhir_resources


def example_fhir_to_cda():
    """Convert FHIR resources to a CDA document."""
    print("\n" + "=" * 60)
    print("Example 2: FHIR to CDA Conversion")
    print("=" * 60)

    # Sample FHIR Bundle
    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-1",
                    "name": [{"given": ["Jane"], "family": "Doe"}],
                    "gender": "female",
                    "birthDate": "1985-07-22",
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-1",
                    "subject": {"reference": "Patient/patient-1"},
                    "code": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "38341003",
                                "display": "Hypertension",
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
                    "onsetDateTime": "2022-03-15",
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationStatement",
                    "id": "med-1",
                    "subject": {"reference": "Patient/patient-1"},
                    "medicationCodeableConcept": {
                        "coding": [
                            {
                                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                                "code": "197361",
                                "display": "Amlodipine 5 MG Oral Tablet",
                            }
                        ]
                    },
                    "status": "active",
                    "dosage": [
                        {
                            "text": "Take 1 tablet by mouth daily",
                            "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}},
                            "doseAndRate": [
                                {
                                    "doseQuantity": {"value": 5, "unit": "mg"}
                                }
                            ],
                        }
                    ],
                }
            },
        ],
    }

    # Create converter
    converter = HealthcareDataConverter()

    # Convert FHIR to CDA
    cda_xml, warnings = converter.fhir_to_cda(
        fhir_bundle,
        document_type=DocumentType.CCD,
        include_narrative=True,
    )

    print(f"\nGenerated CDA document ({len(cda_xml)} bytes)")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")

    # Print first 500 chars of CDA
    print("\nCDA Output (first 500 chars):")
    print(cda_xml[:500] + "...")

    return cda_xml


def example_using_request_model():
    """Using the ConversionRequest model for more control."""
    print("\n" + "=" * 60)
    print("Example 3: Using ConversionRequest Model")
    print("=" * 60)

    # FHIR resources as JSON string
    fhir_json = json.dumps({
        "resourceType": "Condition",
        "id": "example-condition",
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "73211009",
                    "display": "Diabetes mellitus",
                }
            ]
        },
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
        },
    })

    # Create request
    request = ConversionRequest(
        data=fhir_json,
        source_format=ConversionFormat.FHIR,
        target_format=ConversionFormat.CDA,
        document_type=DocumentType.CCD,
        validation_level=ValidationLevel.STRICT,
        include_narrative=True,
        preserve_ids=True,
    )

    # Create converter and convert
    converter = HealthcareDataConverter()
    response = converter.convert(request)

    print(f"\nConversion Status: {response.status.value}")
    print(f"Conversion ID: {response.metadata.conversion_id}")
    print(f"Processing Time: {response.metadata.processing_time_ms}ms")
    print(f"Resources Converted: {response.metadata.resource_count}")

    if response.warnings:
        print(f"\nWarnings:")
        for w in response.warnings:
            print(f"  - {w}")

    if response.errors:
        print(f"\nErrors:")
        for e in response.errors:
            print(f"  - {e}")

    return response


def example_batch_conversion():
    """Demonstrate batch conversion capabilities."""
    print("\n" + "=" * 60)
    print("Example 4: Batch Conversion")
    print("=" * 60)

    # Multiple FHIR conditions
    conditions = [
        {
            "resourceType": "Condition",
            "id": f"condition-{i}",
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": code,
                        "display": display,
                    }
                ]
            },
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
            },
        }
        for i, (code, display) in enumerate([
            ("44054006", "Type 2 diabetes mellitus"),
            ("38341003", "Hypertension"),
            ("195967001", "Asthma"),
            ("13645005", "Chronic obstructive pulmonary disease"),
        ])
    ]

    converter = HealthcareDataConverter()

    print(f"Converting {len(conditions)} conditions to CDA...")

    # Convert each condition
    for condition in conditions:
        request = ConversionRequest(
            data=condition,
            source_format=ConversionFormat.FHIR,
            target_format=ConversionFormat.CDA,
            document_type=DocumentType.CCD,
        )
        response = converter.convert(request)
        print(f"  - {condition['code']['coding'][0]['display']}: {response.status.value}")


def example_validation():
    """Demonstrate validation capabilities."""
    print("\n" + "=" * 60)
    print("Example 5: Validation")
    print("=" * 60)

    converter = HealthcareDataConverter()

    # Valid FHIR resource
    valid_fhir = {
        "resourceType": "Condition",
        "id": "test",
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": "12345"}]},
        "subject": {"reference": "Patient/123"},
    }

    is_valid, messages = converter.validate_fhir(valid_fhir)
    print(f"Valid FHIR: {is_valid}")

    # Invalid FHIR (missing required fields)
    invalid_fhir = {
        "resourceType": "Condition",
        # Missing subject reference
    }

    is_valid, messages = converter.validate_fhir(invalid_fhir)
    print(f"Invalid FHIR: {is_valid}")
    if messages:
        for msg in messages:
            print(f"  - {msg}")


def example_capabilities():
    """Show converter capabilities."""
    print("\n" + "=" * 60)
    print("Example 6: Converter Capabilities")
    print("=" * 60)

    converter = HealthcareDataConverter()
    capabilities = converter.get_capabilities()

    print("\nSupported Conversions:")
    for conv in capabilities.supported_conversions:
        print(f"  {conv['source'].upper()} -> {conv['target'].upper()}")

    print("\nSupported Document Types:")
    for dt in capabilities.supported_document_types:
        print(f"  - {dt}")

    print("\nSupported FHIR Resources:")
    for resource in capabilities.supported_fhir_resources[:5]:
        print(f"  - {resource}")
    print(f"  ... and {len(capabilities.supported_fhir_resources) - 5} more")


if __name__ == "__main__":
    # Run all examples
    example_cda_to_fhir()
    example_fhir_to_cda()
    example_using_request_model()
    example_batch_conversion()
    example_validation()
    example_capabilities()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
