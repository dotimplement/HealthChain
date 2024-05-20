from healthchain.use_cases.cds import ClinicalDecisionSupport
from healthchain.decorators import ehr, api, sandbox
from healthchain.data_generator.data_generator import DataGenerator
import json


def run():
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
            self.data_generator.generate(
                constraints=[
                    "long_encounter_period",
                    "short_encounter_period",
                    "has_problem_list",
                    "has_medication_requests",
                    "has_procedures",
                ],
                free_text_json="./example_free_text.json",
            )

            return self.data_generator.data[-1]

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
    cds.start_sandbox(save_data=False)
    # print(cds.responses)
    # cds.stop_sandbox()

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
