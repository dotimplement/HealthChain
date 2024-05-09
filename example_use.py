from healthchain.use_cases.cds import ClinicalDecisionSupport
from healthchain.decorators import ehr
import dataclasses
import uuid


def Run():
    # ehr = EHR()
    # ehr = EHR.from_doppeldata(data)
    # ehr = EHR.from_path(path)

    # ehr.UseCase = ClinicalDecisionSupport()
    # print(ehr.UseCase)

    # ehr.add_database(data)

    # ehr.send_request("http://0.0.0.0:8000", Workflow("patient-view"))
    # ehr.send_request("http://0.0.0.0:8000", Workflow("notereader-sign-inpatient"))

    @dataclasses.dataclass
    class synth_data:
        context: dict
        uuid: str
        prefetch: dict

    # @sandbox(use_case=ClinicalDecisionSupport())
    class myCDS:
        def __init__(self) -> None:
            self.data_generator = None
            self.use_case = ClinicalDecisionSupport()

        # decorator sets up an instance of ehr configured with use case CDS
        @ehr(workflow="patient-view", num=5)
        def load_data(self, data_spec):
            # data = "hello, " + data_spec
            data = synth_data(
                context={"userId": "Practitioner/123", "patientId": data_spec},
                uuid=str(uuid.uuid4()),
                prefetch={},
            )
            return data

        # @service(langserve=True)
        # def llm(self):
        #     chain = llm | output_parser
        #     return chain

    cds = myCDS()
    ehr_client = cds.load_data("123")
    request = ehr_client.request_data
    for i in range(len(request)):
        print(request[i].model_dump_json(exclude_none=True))


if __name__ == "__main__":
    Run()
