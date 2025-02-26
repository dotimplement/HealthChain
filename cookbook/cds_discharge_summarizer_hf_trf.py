import healthchain as hc

from healthchain.pipeline import SummarizationPipeline
from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.models import Prefetch, CDSRequest, CDSResponse
from healthchain.data_generators import CdsDataGenerator

import getpass
import os


if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass("Enter your token: ")


@hc.sandbox
class DischargeNoteSummarizer(ClinicalDecisionSupport):
    def __init__(self):
        self.pipeline = SummarizationPipeline.from_model_id(
            "google/pegasus-xsum", source="huggingface", task="summarization"
        )
        self.data_generator = CdsDataGenerator()

    @hc.ehr(workflow="encounter-discharge")
    def load_data_in_client(self) -> Prefetch:
        data = self.data_generator.generate_prefetch(
            free_text_path="data/discharge_notes.csv", column_name="text"
        )
        return data

    @hc.api
    def my_service(self, request: CDSRequest) -> CDSResponse:
        result = self.pipeline(request)
        return result


if __name__ == "__main__":
    summarizer = DischargeNoteSummarizer()
    summarizer.start_sandbox()
