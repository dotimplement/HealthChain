# NoteReader Sandbox

A sandbox example of NoteReader clinical documentation improvement which extracts problems, medications, and allergies entries from the progress note section of a pre-configured CDA document using [scispacy](https://github.com/allenai/scispacy) with a custom entity linker component.

Full example coming soon!

```python
import healthchain as hc

from healthchain.io import Document
from healthchain.models.requests import CdaRequest
from healthchain.models.responses import CdaResponse
from healthchain.pipeline import MedicalCodingPipeline
from healthchain.sandbox.use_cases import ClinicalDocumentation
from healthchain.fhir import create_document_reference

from spacy.tokens import Span

from fhir.resources.documentreference import DocumentReference

pipeline = MedicalCodingPipeline.from_model_id("en_core_sci_sm", source="spacy")

@pipeline.add_node(position="after", reference="SpacyNLP")
def link_entities(doc: Document) -> Document:
    # Register the extension if it doesn't exist already
    if not Span.has_extension("cui"):
        Span.set_extension("cui", default=None)
    spacy_doc = doc.nlp.get_spacy_doc()

    dummy_linker = {"fever": "C0006477",
                    "cough": "C0006477",
                    "cold": "C0006477",
                    "flu": "C0006477",
                    "headache": "C0006477",
                    "sore throat": "C0006477",
                    }

    for ent in spacy_doc.ents:
        if ent.text in dummy_linker:
            ent._.cui = dummy_linker[ent.text]

    doc.update_problem_list_from_nlp()

    return doc


@hc.sandbox
class NotereaderSandbox(ClinicalDocumentation):
    def __init__(self):
        self.pipeline = pipeline

    @hc.ehr(workflow="sign-note-inpatient")
    def load_data_in_client(self) -> DocumentReference:
        with open("./resources/uclh_cda.xml", "r") as file:
            xml_string = file.read()

        cda_document_reference = create_document_reference(
            data=xml_string,
            content_type="text/xml",
            description="Original CDA Document loaded from my sandbox",
        )

        return cda_document_reference

    @hc.api
    def my_service(self, request: CdaRequest) -> CdaResponse:
        result = self.pipeline.process_request(request)

        return result


if __name__ == "__main__":
    clindoc = NotereaderSandbox()
    clindoc.start_sandbox()
```
