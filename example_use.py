from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.use_cases.cds import ClinicalDecisionSupport
from healthchain.decorators import ehr, api
from healthchain.service.service import Service

import dataclasses
import uuid


def run():
    @dataclasses.dataclass
    class synth_data:
        context: dict
        uuid: str
        prefetch: dict

    # @sandbox(service_config={"port": "8000"})
    class myCDS(ClinicalDecisionSupport):
        def __init__(self) -> None:
            super().__init__()
            self.data_generator = None
            # TODO: replace this
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

        @api
        def llm(self, text: str):
            print("processing...")
            return {
                "cards": [
                    {
                        "summary": "example",
                        "indicator": "info",
                        "source": {"label": "website"},
                    }
                ]
            }

    cds = myCDS()
    ehr_client = cds.load_data("123")
    request = ehr_client.request_data
    for i in range(len(request)):
        print(request[i].model_dump_json(exclude_none=True))

    cds_dict = {
        "hook": "patient-view",
        "hookInstance": "29e93987-c345-4cb7-9a92-b5136289c2a4",
        "context": {"userId": "Practitioner/123", "patientId": "123"},
    }
    request = CDSRequest(**cds_dict)
    result = cds.llm(request)
    print(result)

    cds.service_api = cds.llm()
    print(cds.service_api)

    service = Service(strategy=cds)

    import threading
    from time import sleep

    server_thread = threading.Thread(target=lambda: service.run())
    server_thread.start()

    sleep(5)

    import asyncio

    responses = asyncio.run(
        ehr_client.send_request(url="http://127.0.0.1:8000/cds-services/1")
    )
    print(responses)


if __name__ == "__main__":
    run()
