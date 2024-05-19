from healthchain.use_cases.cds import ClinicalDecisionSupport
from healthchain.decorators import ehr, api, sandbox
import dataclasses
from pydantic import BaseModel
import random
import json


def run():
    class MockBundle(BaseModel):
        resource: str = "medication"

    @dataclasses.dataclass
    class synth_data:
        context: dict
        resources: MockBundle

    class DataGenerator:
        def __init__(self) -> None:
            self.workflow = None

        def set_workflow(self, workflow):
            self.workflow = workflow

        def generate(self, constraint):
            examples = ["medication", "problems", "procedures"]
            data = MockBundle(resource=random.choice(examples))
            data = synth_data(context={}, resources=data)
            print(
                f"This is synthetic FHIR data from the generator, the param is {constraint}, the workflow is {self.workflow}"
            )

            return data

    @sandbox(service_config={"port": 9000})
    class myCDS(ClinicalDecisionSupport):
        def __init__(self) -> None:
            self.data_generator = DataGenerator()
            self.chain = self.define_chain()

        def define_chain(self):
            return "This will be processed by llm"
            # llm = OpenAI()
            # prompt = ""
            # parser = JsonOutputParser()
            # chain = prompt | llm | parser
            # return chain

        # decorator sets up an instance of ehr configured with use case CDS
        @ehr(workflow="encounter-discharge", num=3)
        def load_data(self):
            data = self.data_generator.generate(constraint=["long_duration"])
            return data

        @api
        def llm(self, text: str):
            # result = self.chain.invoke(text)
            # return result
            print(text)
            request = json.loads(text)
            prefetch = request.get("prefetch")
            resource = prefetch.get("resource", "")
            return {
                "cards": [
                    {
                        "summary": self.chain,
                        "indicator": "info",
                        "source": {"label": resource},
                    }
                ]
            }

    cds = myCDS()
    cds.start_sandbox()
    print(cds.responses)

    # ehr_client = cds.load_data("123")
    # request = ehr_client.request_data
    # for i in range(len(request)):
    #     print(request[i].model_dump_json(exclude_none=True))

    # cds_dict = {
    #     "hook": "patient-view",
    #     "hookInstance": "29e93987-c345-4cb7-9a92-b5136289c2a4",
    #     "context": {"userId": "Practitioner/123", "patientId": "123"},
    # }
    # request = CDSRequest(**cds_dict)
    # result = cds.llm(request)
    # print(result)


if __name__ == "__main__":
    run()
