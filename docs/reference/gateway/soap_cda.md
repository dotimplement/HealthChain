# SOAP/CDA Protocol

The SOAP/CDA protocol enables real-time Clinical Documentation Improvement (CDI) services. This implementation follows the Epic-integrated NoteReader CDI specification for analyzing clinical notes and extracting structured data.

## Overview

Clinical Documentation workflows communicate using [CDA (Clinical Document Architecture)](https://www.hl7.org.uk/standards/hl7-standards/cda-clinical-document-architecture/). CDAs are standardized electronic documents for exchanging clinical information between different healthcare systems. They provide a common structure for capturing and sharing patient data like medical history, medications, and care plans between different healthcare systems and providers. Think of it as a collaborative Google Doc that you can add, amend, and remove entries from. CDA support is currently limited to [Epic systems](https://open.epic.com/clinical/ehrtoehr), but we plan to add support for other IHE SOAP/CDA services in the future.

### Epic NoteReader CDI

The Epic NoteReader CDI is a SOAP/CDA-based NLP service that extracts structured data from clinical notes. Like CDS Hooks, it operates in real-time and is triggered when a clinician opts into CDI functionality and signs or pends a note.

The primary use case for Epic NoteReader is to convert free-text medical documentation into coded information that can be used for billing, quality reporting, continuity of care, and clinical decision support at the point-of-care ([example](https://bmcmedinformdecismak.biomedcentral.com/articles/10.1186/s12911-025-03195-1)).


| When      | Where | What you receive            | What you send back         |
| :-------- | :-----| :-------------------------- |----------------------------|
| Triggered when a clinician opts in to CDI functionality and signs or pends a note | EHR documentation modules (e.g. NoteReader in Epic) | A CDA document containing continuity of care data and free-text clinical notes | A CDA document with additional structured data extracted by your CDI service |


### CDA Services

CDA services facilitate the [exchange of clinical information between different healthcare systems](https://gkc.himss.org/resource-environmental-scan/care-everywhere) and are governed by the [IHE](https://www.ihe.net/uploadedFiles/Documents/PCC/IHE_PCC_Suppl_CDA_Content_Modules.pdf) standard. The Epic HIE (Health Information Exchange) platform is [CareEverywhere](https://www.epic.com/careeverywhere/).


## HealthChainAPI Integration

Use the `NoteReaderService` with HealthChainAPI to handle SOAP/CDA workflows:

```python
from healthchain.gateway import HealthChainAPI, NoteReaderService
from healthchain.models import CdaRequest, CdaResponse

app = HealthChainAPI()
notes = NoteReaderService()

@notes.method("ProcessDocument")
def process_note(request: CdaRequest) -> CdaResponse:
    # Your NLP pipeline here
    processed_document = nlp_pipeline.process(request)
    return processed_document

app.register_service(notes, path="/soap")
```

## Supported Workflows

| Workflow Name | Description | Trigger | Status |
|-----------|-------------|---------|----------|
| `sign-note-inpatient` | CDI processing for inpatient clinical notes | Signing or pending a note in Epic inpatient setting | ✅ |
| `sign-note-outpatient` | CDI processing for outpatient clinical notes | Signing or pending a note in Epic outpatient setting | ⏳ |

Currently supports parsing of problems, medications, and allergies sections.

## API Endpoints

When registered with HealthChainAPI, the following endpoints are automatically created:

| Endpoint | Method | Function | Protocol |
|------|--------|----------|----------|
| `/notereader/` | POST | `process_notereader_document` | SOAP |

*Note: NoteReader is a vendor-specific component (Epic). Different EHR vendors have varying support for third-party CDI services.*

## Request/Response Format

### CDA Request Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
  <templateId root="2.16.840.1.113883.10.20.22.1.2"/>
  <id root="2.16.840.1.113883.19.5.99999.1"/>
  <code code="34133-9" displayName="Summarization of Episode Note"
        codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
  <title>CDA Document with Problem List and Progress Note</title>
  <effectiveTime value="20240712"/>
  <confidentialityCode code="N" codeSystem="2.16.840.1.113883.5.25"/>
  <languageCode code="en-US"/>

  <component>
    <structuredBody>
      <!-- Problem List Section -->
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.5.1"/>
          <code code="11450-4" codeSystem="2.16.840.1.113883.6.1"
                displayName="Problem List"/>
          <title>Problems</title>
          <text>
            <list>
              <item>Hypertension</item>
            </list>
          </text>
          <!-- Entry details... -->
        </section>
      </component>

      <!-- Progress Note Section -->
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.65"/>
          <code code="11506-3" codeSystem="2.16.840.1.113883.6.1"
                displayName="Progress Note"/>
          <title>Progress Note</title>
          <text>
            <paragraph>Patient's blood pressure remains elevated.
            Discussed lifestyle modifications and medication adherence.
            Started Lisinopril 10 mg daily for hypertension management.</paragraph>
          </text>
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>
```

### CDA Response Example

The response includes additional structured sections extracted from the clinical text:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <!-- Header information same as request -->

  <component>
    <structuredBody>
      <!-- Original sections plus extracted medications -->
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.1.1"/>
          <code code="10160-0" codeSystem="2.16.840.1.113883.6.1"
                displayName="History of medication use"/>
          <title>Medications</title>
          <text>
            <list>
              <item>Lisinopril 10 mg oral tablet, once daily</item>
            </list>
          </text>
          <!-- Structured medication entries extracted by AI... -->
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>
```

## Supported CDA Sections

- **Problems/Conditions**: ICD-10/SNOMED CT coded diagnoses
- **Medications**: SNOMED CT/RxNorm coded medications with dosage and frequency
- **Allergies**: Allergen identification and reaction severity
- **Progress Notes**: Free-text clinical documentation

## Data Flow

| Stage | Input | Output |
|-------|-------|--------|
| Gateway Receives | `CdaRequest` | Processed by your service |
| Gateway Returns | Your processed result | `CdaResponse` |

You can use the [CdaAdapter](../io/adapters/cdaadapter.md) to handle conversion between CDA documents and HealthChain pipeline data containers.
