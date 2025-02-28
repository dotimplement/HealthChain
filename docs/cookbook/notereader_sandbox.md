# NoteReader Sandbox

A sandbox example of NoteReader clinical documentation improvement which extracts problems, medications, and allergies entries from the progress note section of a pre-configured CDA document.

Full example coming soon!

```python
import healthchain as hc
from healthchain.use_cases import ClinicalDocumentation
from healthchain.fhir import create_document_reference

from fhir.resources.documentreference import DocumentReference


@hc.sandbox
class NotereaderSandbox(ClinicalDocumentation):
  def __init__(self):
      self.cda_path = "./resources/uclh_cda.xml"
      self.pipeline = MedicalCodingPipeline.from_local_model(
          "./resources/models/medcat_model.zip", source="spacy"
      )

  @hc.ehr(workflow="sign-note-inpatient")
  def load_data_in_client(self) -> DocumentReference:
    with open(self.cda_path, "r") as file:
        xml_string = file.read()

    cda_document_reference = create_document_reference(
        data=xml_string,
        content_type="text/xml",
        description="Original CDA Document loaded from my sandbox",
    )
    return cda_document_reference

  @hc.api
  def my_service(self, request: CdaRequest) -> CdaResponse:
    response = self.pipeline(request)
    return response
```
