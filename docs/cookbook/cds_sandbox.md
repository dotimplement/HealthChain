# Build a CDS sandbox

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
