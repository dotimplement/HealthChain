import healthchain as hc
from healthchain.gateway import HealthChainAPI, CDSHooksService
from healthchain.pipeline import SummarizationPipeline
from healthchain.sandbox.use_cases import ClinicalDecisionSupport
from healthchain.models import Prefetch, CDSRequest, CDSResponse
from healthchain.data_generators import CdsDataGenerator

import getpass
import os


if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass("Enter your token: ")


# Create the healthcare application
app = HealthChainAPI(
    title="Discharge Note Summarizer",
    description="AI-powered discharge note summarization service",
)

# Initialize pipeline
pipeline = SummarizationPipeline.from_model_id(
    "google/pegasus-xsum", source="huggingface", task="summarization"
)

# Create CDS Hooks service
cds = CDSHooksService()


@cds.hook("encounter-discharge", id="discharge-summarizer")
def discharge_summarizer(request: CDSRequest) -> CDSResponse:
    result = pipeline.process_request(request)
    return result


# Register the CDS service
app.register_service(cds, path="/cds")


@hc.sandbox(api="http://localhost:8000")
class DischargeNoteSummarizer(ClinicalDecisionSupport):
    def __init__(self):
        super().__init__(path="/cds/cds-services/discharge-summarizer")
        self.data_generator = CdsDataGenerator()

    @hc.ehr(workflow="encounter-discharge")
    def load_data_in_client(self) -> Prefetch:
        data = self.data_generator.generate_prefetch(
            free_text_path="data/discharge_notes.csv", column_name="text"
        )
        return data


if __name__ == "__main__":
    import uvicorn
    import threading

    # Start the API server in a separate thread
    def start_api():
        uvicorn.run(app, port=8000)

    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    # Start the sandbox
    summarizer = DischargeNoteSummarizer()
    summarizer.start_sandbox()
