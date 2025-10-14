# Basic Format Conversion

This tutorial demonstrates how to use the HealthChain interoperability module to convert between different healthcare data formats.

## Prerequisites

- HealthChain installed (`pip install healthchain`)
- Basic understanding of FHIR resources
- Sample CDA or HL7v2 files (or you can use the examples below)

## Setup

First, let's import the required modules and create an interoperability engine:

```python
from healthchain.interop import create_interop, FormatType
from pathlib import Path
import json

# Create an engine
engine = create_interop()
```

## Converting CDA to FHIR

Let's convert a CDA document to FHIR resources:

```python
# Sample CDA document
cda_xml = """
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <templateId root="2.16.840.1.113883.10.20.22.1.2"/>
  <id root="2.16.840.1.113883.19.5.99999.1"/>
  <code code="34133-9" displayName="Summarization of Episode Note" codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
  <title>Example CDA Document</title>
  <effectiveTime value="20150519"/>
  <confidentialityCode code="N" codeSystem="2.16.840.1.113883.5.25"/>
  <languageCode code="en-US"/>
  <recordTarget>
    <patientRole>
      <id extension="12345" root="2.16.840.1.113883.19.5.99999.2"/>
      <patient>
        <name>
          <given>John</given>
          <family>Smith</family>
        </name>
        <administrativeGenderCode code="M" codeSystem="2.16.840.1.113883.5.1"/>
        <birthTime value="19701101"/>
      </patient>
    </patientRole>
  </recordTarget>
  <component>
    <structuredBody>
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.1.11"/>
          <code code="11450-4" codeSystem="2.16.840.1.113883.6.1" displayName="Problem List"/>
          <title>Problems</title>
          <text>Hypertension</text>
          <entry>
            <observation classCode="OBS" moodCode="EVN">
              <templateId root="2.16.840.1.113883.10.20.1.28"/>
              <templateId root="2.16.840.1.113883.10.20.1.54"/>
              <id root="2.16.840.1.113883.19.5.99999.3"/>
              <code code="64572001" displayName="Hypertension" codeSystem="2.16.840.1.113883.6.96" codeSystemName="SNOMED CT"/>
              <statusCode code="completed"/>
              <effectiveTime value="20180101"/>
              <value xsi:type="CD" code="64572001" displayName="Hypertension" codeSystem="2.16.840.1.113883.6.96" codeSystemName="SNOMED CT" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
            </observation>
          </entry>
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>
"""

# Convert CDA to FHIR resources
fhir_resources = engine.to_fhir(cda_xml, src_format=FormatType.CDA)

# Print the resulting FHIR resources
for resource in fhir_resources:
    print(f"Resource Type: {resource.resource_type}")
    print(json.dumps(resource.dict(), indent=2))
    print("-" * 40)
```

## Converting FHIR to CDA

You can also convert FHIR resources to a CDA document:

```python
from fhir.resources.condition import Condition
from fhir.resources.patient import Patient

# Create some FHIR resources
patient = Patient(
    resourceType="Patient",
    id="patient-1",
    name=[{"family": "Smith", "given": ["John"]}],
    gender="male",
    birthDate="1970-11-01"
)

condition = Condition(
    resourceType="Condition",
    id="condition-1",
    subject={"reference": "Patient/patient-1"},
    code={
        "coding": [
            {
                "system": "http://snomed.info/sct",
                "code": "38341003",
                "display": "Hypertension"
            }
        ],
        "text": "Hypertension"
    },
    clinicalStatus={
        "coding": [
            {
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }
        ]
    },
    verificationStatus={
        "coding": [
            {
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }
        ]
    },
    onsetDateTime="2018-01-01"
)

# Convert FHIR resources to CDA
resources = [patient, condition]
cda_document = engine.from_fhir(resources, dest_format=FormatType.CDA)

# Print the resulting CDA document
print(cda_document)
```

## Converting HL7v2 to FHIR

Let's convert an HL7v2 message to FHIR resources:

```python
# Sample HL7v2 message
hl7v2_message = """
MSH|^~\&|EPIC|EPICADT|SMS|SMSADT|199912271408|CHARRIS|ADT^A01|1817457|D|2.5|
PID|1||PATID1234^5^M11^ADT1^MR^GOOD HEALTH HOSPITAL~123456789^^^USSSA^SS||EVERYMAN^ADAM^A^III||19610615|M||C|2222 HOME STREET^^GREENSBORO^NC^27401-1020|GL|(555) 555-2004|(555)555-2004||S||PATID12345001^2^M10^ADT1^AN^A|444333333|987654^NC|
NK1|1|NUCLEAR^NELDA^W|SPO||(555)555-3333||EC|||||||||||||||||||||||||
PV1|1|I|2000^2012^01||||004777^ATTEND^AARON^A|||SUR||||ADM|A0|
"""

# Convert HL7v2 to FHIR resources
fhir_resources = engine.to_fhir(hl7v2_message, src_format=FormatType.HL7V2)

# Print the resulting FHIR resources
for resource in fhir_resources:
    print(f"Resource Type: {resource.resource_type}")
    print(json.dumps(resource.dict(), indent=2))
    print("-" * 40)
```

## Converting FHIR to HL7v2

You can also convert FHIR resources to an HL7v2 message:

```python
from fhir.resources.patient import Patient
from fhir.resources.encounter import Encounter

# Create some FHIR resources
patient = Patient(
    resourceType="Patient",
    id="patient-1",
    name=[{"family": "Everyman", "given": ["Adam", "A"], "suffix": ["III"]}],
    gender="male",
    birthDate="1961-06-15",
    identifier=[
        {
            "system": "urn:oid:1.2.36.146.595.217.0.1",
            "value": "PATID1234"
        }
    ],
    address=[
        {
            "line": ["2222 Home Street"],
            "city": "Greensboro",
            "state": "NC",
            "postalCode": "27401"
        }
    ],
    telecom=[
        {
            "system": "phone",
            "value": "(555) 555-2004",
            "use": "home"
        }
    ]
)

encounter = Encounter(
    resourceType="Encounter",
    id="encounter-1",
    status="finished",
    class_fhir={
        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
        "code": "IMP",
        "display": "inpatient encounter"
    },
    subject={
        "reference": "Patient/patient-1"
    }
)

# Convert FHIR resources to HL7v2
resources = [patient, encounter]
hl7v2_message = engine.from_fhir(resources, dest_format=FormatType.HL7V2)

# Print the resulting HL7v2 message
print(hl7v2_message)
```

## Saving Conversion Results

Let's save our conversion results to files:

```python
# Save FHIR resources to JSON files
output_dir = Path("./output")
output_dir.mkdir(exist_ok=True)

for resource in fhir_resources:
    filename = f"{resource.resource_type.lower()}_{resource.id}.json"
    with open(output_dir / filename, "w") as f:
        json.dump(resource.dict(), f, indent=2)

# Save CDA document to XML file
with open(output_dir / "document.xml", "w") as f:
    f.write(cda_document)

# Save HL7v2 message to file
with open(output_dir / "message.hl7", "w") as f:
    f.write(hl7v2_message)
```

## Conclusion

In this tutorial, you learned how to:

- Convert CDA documents to FHIR resources
- Convert FHIR resources to CDA documents
- Convert HL7v2 messages to FHIR resources
- Convert FHIR resources to HL7v2 messages
- Save conversion results to files

For more advanced interoperability features, see the [InteropEngine documentation](../../reference/interop/engine.md) and other cookbook examples.
