from src.simulator.ehr import EHR, UseCaseType, Workflow
from src.use_cases.cds import ClinicalDecisionSupport
from src.decorators import ehr


def Run():
    # ehr = EHR()
    # ehr = EHR.from_doppeldata(data)
    # ehr = EHR.from_path(path)

    # ehr.UseCase = ClinicalDecisionSupport()
    # print(ehr.UseCase)

    # ehr.add_database(data)

    # ehr.send_request("http://0.0.0.0:8000", Workflow("patient-view"))
    # ehr.send_request("http://0.0.0.0:8000", Workflow("notereader-sign-inpatient"))

    class myCDS:
        def __init__(self) -> None:
            self.data_generator = None

        # decorator sets up an instance of ehr configured with use case CDS
        @ehr(use_case=ClinicalDecisionSupport(), workflow="patient-view")
        def trigger(self, data_spec):
            data = "hello, " + data_spec
            return data

        # @service(langserve=True)
        # def LLM(self):
        #     chain = llm | output_parser
        #     return chain

    request = myCDS().trigger("lady whiskerson")
    print(request)


if __name__ == "__main__":
    Run()
