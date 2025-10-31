import os
import getpass

from healthchain.gateway import HealthChainAPI, CDSHooksService
from healthchain.pipeline import SummarizationPipeline
from healthchain.models import CDSRequest, CDSResponse

from dotenv import load_dotenv

load_dotenv()


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


if __name__ == "__main__":
    import uvicorn
    import threading

    from healthchain.sandbox import SandboxClient

    # Start the API server in a separate thread
    def start_api():
        uvicorn.run(app, port=8000)

    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    # Create sandbox client and load test data
    client = SandboxClient(
        url="http://localhost:8000/cds/cds-services/discharge-summarizer",
        workflow="encounter-discharge",
    )
    # Load discharge notes from CSV
    client.load_free_text(
        csv_path="data/discharge_notes.csv",
        column_name="text",
    )
    # Send requests and get responses
    responses = client.send_requests()

    # Save results
    client.save_results("./output/")

    try:
        api_thread.join()
    except KeyboardInterrupt:
        pass
