import json
import pytest

from healthchain.clients import ehr
from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.decorators import api, sandbox
from healthchain.data_generators import CdsDataGenerator
from healthchain.models import CDSRequest


@pytest.mark.skip(reason="Server hangs during test.")
def test_run():
    @sandbox(service_config={"port": 9000})
    class myCDS(ClinicalDecisionSupport):
        def __init__(self) -> None:
            self.data_generator = CdsDataGenerator()
            self.chain = self.define_chain()

        def define_chain(self):
            return "This will be processed by llm"

        # decorator sets up an instance of ehr configured with use case CDS
        @ehr(workflow="encounter-discharge", num=3)
        def load_data(self):
            data = self.data_generator.generate_prefetch(constraints=["long_duration"])
            return data

        @api
        def llm(self, text: str):
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

    ehr_client = cds.load_data()
    request = ehr_client.request_data

    cds_dict = {
        "hook": "patient-view",
        "hookInstance": "29e93987-c345-4cb7-9a92-b5136289c2a4",
        "context": {"userId": "Practitioner/123", "patientId": "123"},
    }
    request = CDSRequest(**cds_dict)
    result = cds.llm(request)
    assert result["cards"][0]["summary"] == "This will be processed by llm"
