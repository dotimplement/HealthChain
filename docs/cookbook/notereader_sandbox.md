# NoteReader Sandbox

A sandbox example of NoteReader clinical documentation improvement which extracts problems, medications, and allergies entries from the progress note section of a pre-configured CDA document.

```python
import healthchain as hc
from healthchain.use_cases import ClinicalDocumentation
from healthchain.models import (
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
      self.cda_path = "./resources/uclh_cda.xml"

  @hc.ehr(workflow="sign-note-inpatient")
  def load_data_in_client(self) -> CcdData:
      with open(self.cda_path, "r") as file:
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
