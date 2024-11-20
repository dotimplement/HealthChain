# NoteReader Sandbox

A sandbox example of NoteReader clinical documentation improvement which extracts problems, medications, and allergies entries from the progress note section of a pre-configured CDA document.

Full example coming soon!

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
      self.pipeline = MedicalCodingPipeline.from_local_model(
          "./resources/models/medcat_model.zip", source="spacy"
      )

  @hc.ehr(workflow="sign-note-inpatient")
  def load_data_in_client(self) -> CcdData:
      with open(self.cda_path, "r") as file:
          xml_string = file.read()

      return CcdData(cda_xml=xml_string)

  @hc.api
  def my_service(self, request: CdaRequest) -> CdaResponse:
    response = self.pipeline(request)
    return response
```
