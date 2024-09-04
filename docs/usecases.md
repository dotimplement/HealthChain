# Use Cases

## Clinical Decision Support (CDS)

[CDS Hooks](https://cds-hooks.org/) is an [HL7](https://cds-hooks.hl7.org) published specification for clinical decision support. For more information please consult the [official documentation](https://cds-hooks.org/).

| When      | Where | What you receive            | What you send back         |
| :-------- | :-----| :-------------------------- |----------------------------|
| Triggered at certain events during a clinician's workflow, e.g. when a patient record is opened. | EHR  | The context of the event and FHIR resources that are requested by your service. e.g. patient ID, `Encounter` and `Patient`.  | “Cards” displaying text, actionable suggestions, or links to launch a [SMART](https://smarthealthit.org/) app from within the workflow.      |


Each workflow has associated `context` and `prefetch` FHIR resource returned from it.

If you use the `DataGenerator`, a pre-configured list of FHIR resources is randomly generated and placed in the `prefetch` field of a `CDSRequest`.

Current implemented workflows:

| Workflow      | Implementation Completeness        | Generated Synthetic Resources |
| ----------- | ------------------------------------ | -----------------------------
| [patient-view](https://cds-hooks.org/hooks/patient-view/) | :material-check-all:  | `Patient`, `Encounter` (Future: `MedicationStatement`, `AllergyIntolerance`)|
| [encounter-discharge](https://cds-hooks.org/hooks/encounter-discharge/)| :material-check-all: | `Patient`, `Encounter`, `Procedure`, `MedicationRequest`, Optional `DocumentReference` |
| [order-sign](https://cds-hooks.org/hooks/order-sign/)| :material-check: Partial | Future: `MedicationRequest`, `ProcedureRequest`, `ServiceRequest` |
| [order-select](https://cds-hooks.org/hooks/order-select/) | :material-check: Partial | Future: `MedicationRequest`, `ProcedureRequest`, `ServiceRequest` |


### Example `CDSRequest`

```json
{
   "hookInstance" : "23f1a303-991f-4118-86c5-11d99a39222e",
   "fhirServer" : "https://fhir.example.org",
   "hook" : "patient-view",
   "context" : {
     "patientId" : "1288992",
     "userId" : "Practitioner/example"
    },
   "prefetch" : {
      "patientToGreet" : {
        "resourceType" : "Patient",
        "gender" : "male",
        "birthDate" : "1925-12-23",
        "id" : "1288992",
        "active" : true
      }
   }
}
```
### Example `CDSResponse`

```json
{
  "summary": "Bilirubin: Based on the age of this patient consider overlaying bilirubin [Mass/volume] results over a time-based risk chart",
  "indicator": "info",
  "detail": "The focus of this app is to reduce the incidence of severe hyperbilirubinemia and bilirubin encephalopathy while minimizing the risks of unintended harm such as maternal anxiety, decreased breastfeeding, and unnecessary costs or treatment.",
  "source": {
    "label": "Intermountain",
    "url": null
  },
  "links": [
    {
      "label": "Bilirubin SMART app",
      "url": "https://example.com/launch",
      "type": "smart"
   }
  ]
}

```

### Implemented FHIR Resources

- `Patient`
- `Encounter`
- `Procedure`
- `MedicationRequest`

### Example Sandbox Usage

A CDS sandbox which uses `gpt-4o` to summarise patient information from synthetically generated FHIR resources received from the `patient-view` CDS hook.

```python
import healthchain as hc
from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.data_generators import CdsDataGenerator
from healthchain.models import Card, CdsFhirData, CDSRequest

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from typing import List

@hc.sandbox
class CdsSandbox(ClinicalDecisionSupport):
  def __init__(self):
    self.chain = self._init_llm_chain()
    self.data_generator = CdsDataGenerator()

  def _init_llm_chain(self):
    prompt = PromptTemplate.from_template(
      "Extract conditions from the FHIR resource below and summarize in one sentence using simple language \n'''{text}'''"
      )
    model = ChatOpenAI(model="gpt-4o")
    parser = StrOutputParser()

    chain = prompt | model | parser
    return chain

  @hc.ehr(workflow="patient-view")
  def load_data_in_client(self) -> CdsFhirData:
    data = self.data_generator.generate()
    return data

  @hc.api
  def my_service(self, request: CDSRequest) -> List[Card]:
    result = self.chain.invoke(str(request.prefetch))
    return Card(
      summary="Patient summary",
      indicator="info",
      source={"label": "openai"},
      detail=result,
    )
```

## Clinical Documentation
The `ClinicalDocumentation` use case implements a real-time Clinical Documentation Improvement (CDI) service. It currently implements the Epic-integrated NoteReader CDI specification, which communicates with a third-party natural language processing (NLP) engine to analyse clinical notes and extract structured data. It helps convert free-text medical documentation into coded information that can be used for billing, quality reporting, and clinical decision support.

`ClinicalDocumentation` communicates using [CDAs (Clinical Document Architecture)](https://www.hl7.org/implement/standards/product_brief.cfm?product_id=7). CDAs are standardised electronic documents for exchanging clinical information. They provide a common structure for capturing and sharing patient data like medical history, medications, and care plans between different healthcare systems and providers. Think of it as a collaborative Google Doc that you can add, amend, and remove entries from. CDAs typically uses a SOAP-based communication protocol (unfortunately).

Note that NoteReader is a vendor-specific component (Epic). This particular note-based workfow is one type of CDI service. Different EHR vendors will have different support for third-party CDI services.

In HealthChain, the workflow is named `sign-note-inpatient`. We support parsing of problems, medications, and allergies sections, though some of the data fields may be limited. We plan to implement additional CDI services and workflows for different vendor specifications.

The `DataGenerator` currently does not support synthetic CDA data - we're working on it! At the moment, you can only load and return a pre-existing CDA from your sandbox api function.

| When      | Where | What you receive            | What you send back         |
| :-------- | :-----| :-------------------------- |----------------------------|
| Triggered when a clinician opts in to a CDI functionality and signs or pends a note after writing it. | Specific modules in EHR where clinical documentation takes place, such as NoteReader in Epic.  | A CDA document which contains continuity of care data and free-text data, e.g. a patient's problem list and the progress note that the clinician has entered in the EHR.  | A CDA document which contains additional structured data extracted and returned by your CDI service. |

### Example `CdaRequest`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
  <templateId root="2.16.840.1.113883.10.20.22.1.2"/>
  <id root="2.16.840.1.113883.19.5.99999.1"/>
  <code code="34133-9" displayName="Summarization of Episode Note" codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
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
          <code code="11450-4" codeSystem="2.16.840.1.113883.6.1" displayName="Problem List"/>
          <title>Problems</title>
          <text>
            <list>
              <item>Hypertension</item>
            </list>
          </text>
          <entry>
            <act classCode="ACT" moodCode="EVN">
              <templateId root="2.16.840.1.113883.10.20.22.4.3"/>
              <id root="ab1791b0-5c71-11db-b0de-0800200c9a66"/>
              <code code="CONC" codeSystem="2.16.840.1.113883.5.6"/>
              <statusCode code="active"/>
              <effectiveTime>
                <low value="20240712"/>
              </effectiveTime>
              <entryRelationship typeCode="SUBJ">
                <observation classCode="OBS" moodCode="EVN">
                  <templateId root="2.16.840.1.113883.10.20.22.4.4"/>
                  <id root="ab1791b0-5c71-11db-b0de-0800200c9a66"/>
                  <code code="55607006" displayName="Problem" codeSystem="2.16.840.1.113883.6.96" codeSystemName="SNOMED CT"/>
                  <text>Hypertension</text>
                  <statusCode code="completed"/>
                  <effectiveTime>
                    <low value="20240712"/>
                  </effectiveTime>
                  <value xsi:type="CD" code="59621000" displayName="Essential hypertension" codeSystem="2.16.840.1.113883.6.96" codeSystemName="SNOMED CT"/>
                </observation>
              </entryRelationship>
            </act>
          </entry>
        </section>
      </component>

      <!-- Progress Note Section -->
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.65"/>
          <code code="11506-3" codeSystem="2.16.840.1.113883.6.1" displayName="Progress Note"/>
          <title>Progress Note</title>
          <text>
            <paragraph>Patient's blood pressure remains elevated. Discussed lifestyle modifications and medication adherence. Started Lisinopril 10 mg daily for hypertension management. Will follow up in 3 months to assess response to treatment.</paragraph>
          </text>
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>
```

### Example `CdaResponse`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
  <templateId root="2.16.840.1.113883.10.20.22.1.2"/>
  <id root="2.16.840.1.113883.19.5.99999.1"/>
  <code code="34133-9" displayName="Summarization of Episode Note" codeSystem="2.16.840.1.113883.6.1" codeSystemName="LOINC"/>
  <title>CDA Document with Problem List, Medication, and Progress Note</title>
  <effectiveTime value="20240712"/>
  <confidentialityCode code="N" codeSystem="2.16.840.1.113883.5.25"/>
  <languageCode code="en-US"/>

  <component>
    <structuredBody>
      <!-- Problem List Section -->
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.5.1"/>
          <code code="11450-4" codeSystem="2.16.840.1.113883.6.1" displayName="Problem List"/>
          <title>Problems</title>
          <text>
            <list>
              <item>Hypertension</item>
            </list>
          </text>
          <entry>
            <act classCode="ACT" moodCode="EVN">
              <templateId root="2.16.840.1.113883.10.20.22.4.3"/>
              <id root="ab1791b0-5c71-11db-b0de-0800200c9a66"/>
              <code code="CONC" codeSystem="2.16.840.1.113883.5.6"/>
              <statusCode code="active"/>
              <effectiveTime>
                <low value="20240712"/>
              </effectiveTime>
              <entryRelationship typeCode="SUBJ">
                <observation classCode="OBS" moodCode="EVN">
                  <templateId root="2.16.840.1.113883.10.20.22.4.4"/>
                  <id root="ab1791b0-5c71-11db-b0de-0800200c9a66"/>
                  <code code="55607006" displayName="Problem" codeSystem="2.16.840.1.113883.6.96" codeSystemName="SNOMED CT"/>
                  <text>Hypertension</text>
                  <statusCode code="completed"/>
                  <effectiveTime>
                    <low value="20240712"/>
                  </effectiveTime>
                  <value xsi:type="CD" code="59621000" displayName="Essential hypertension" codeSystem="2.16.840.1.113883.6.96" codeSystemName="SNOMED CT"/>
                </observation>
              </entryRelationship>
            </act>
          </entry>
        </section>
      </component>

      <!-- Medications Section -->
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.1.1"/>
          <code code="10160-0" codeSystem="2.16.840.1.113883.6.1" displayName="History of medication use"/>
          <title>Medications</title>
          <text>
            <list>
              <item>Lisinopril 10 mg oral tablet, once daily</item>
            </list>
          </text>
          <entry>
            <substanceAdministration classCode="SBADM" moodCode="EVN">
              <templateId root="2.16.840.1.113883.10.20.22.4.16"/>
              <id root="cdbd33f0-6cde-11db-9fe1-0800200c9a66"/>
              <statusCode code="active"/>
              <effectiveTime xsi:type="IVL_TS">
                <low value="20240712"/>
              </effectiveTime>
              <routeCode code="PO" codeSystem="2.16.840.1.113883.5.112" displayName="Oral"/>
              <doseQuantity value="1"/>
              <administrationUnitCode code="C48542" displayName="Tablet" codeSystem="2.16.840.1.113883.3.26.1.1"/>
              <consumable>
                <manufacturedProduct classCode="MANU">
                  <templateId root="2.16.840.1.113883.10.20.22.4.23"/>
                  <manufacturedMaterial>
                    <code code="197884" codeSystem="2.16.840.1.113883.6.88" displayName="Lisinopril 10 MG Oral Tablet">
                      <originalText>Lisinopril 10 mg oral tablet</originalText>
                    </code>
                  </manufacturedMaterial>
                </manufacturedProduct>
              </consumable>
              <entryRelationship typeCode="SUBJ">
                <observation classCode="OBS" moodCode="EVN">
                  <templateId root="2.16.840.1.113883.10.20.22.4.20"/>
                  <code code="33999-4" codeSystem="2.16.840.1.113883.6.1" displayName="Indication"/>
                  <value xsi:type="CD" code="59621000" displayName="Essential hypertension" codeSystem="2.16.840.1.113883.6.96"/>
                </observation>
              </entryRelationship>
            </substanceAdministration>
          </entry>
        </section>
      </component>

      <!-- Progress Note Section -->
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.65"/>
          <code code="11506-3" codeSystem="2.16.840.1.113883.6.1" displayName="Progress Note"/>
          <title>Progress Note</title>
          <text>
            <paragraph>Patient's blood pressure remains elevated. Discussed lifestyle modifications and medication adherence. Started Lisinopril 10 mg daily for hypertension management. Will follow up in 3 months to assess response to treatment.</paragraph>
          </text>
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>
```

### Implemented CDA Sections
- Problems
- Medications (including information on dosage, frequency, duration, route)
- Allergies (including information on severity, reaction and type of allergen)
- Progress Note (free-text)

### Example Sandbox Usage
A sandbox example of NoteReader clinical documentation improvement which extracts problems, medications, and allergies entries from the progress note section of a pre-configured CDA document.

```python
import healthchain as hc
from healthchain.use_cases import ClinicalDocumentation
from healthchain.models.data.concept import (
    CcdData,
    AllergyConcept,
    Concept,
    MedicationConcept,
    ProblemConcept,
    Quantity,
)

@hc.sandbox
class NotereaderSandbox(ClinicalDocumentation):
  def __init__(self):
      self.overwrite = True

  @hc.ehr(workflow="sign-note-inpatient")
  def load_data_in_client(self) -> CcdData:
      with open("./resources/uclh_cda.xml", "r") as file:
          xml_string = file.read()

      return CcdData(cda_xml=xml_string)

  @hc.api
  def my_service(self, ccd_data: CcdData) -> CcdData:

    # Apply extraction method from ccd_data.note

    new_problem = ProblemConcept(
      code="38341003",
      code_system="2.16.840.1.113883.6.96",
      code_system_name="SNOMED CT",
      display_name="Hypertension",
    )
    new_allergy = AllergyConcept(
      code="70618",
      code_system="2.16.840.1.113883.6.96",
      code_system_name="SNOMED CT",
      display_name="Allergy to peanuts",
    )
    new_medication = MedicationConcept(
      code="197361",
      code_system="2.16.840.1.113883.6.88",
      code_system_name="RxNorm",
      display_name="Lisinopril 10 MG Oral Tablet",
      dosage=Quantity(value=10, unit="mg"),
      route=Concept(
        code="26643006",
        code_system="2.16.840.1.113883.6.96",
        code_system_name="SNOMED CT",
        display_name="Oral",
      ),
    )
    ccd_data.problems = [new_problem]
    ccd_data.allergies = [new_allergy]
    ccd_data.medications = [new_medication]

    return ccd_data
```
