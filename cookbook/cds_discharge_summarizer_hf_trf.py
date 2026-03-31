#!/usr/bin/env python3
"""
Discharge Note Summarizer (Transformer)

CDS Hooks service that summarises discharge notes using a fine-tuned
HuggingFace transformer model (PEGASUS).

Requirements:
    pip install healthchain transformers torch python-dotenv
    # HUGGINGFACEHUB_API_TOKEN env var required

Run:
    python cookbook/cds_discharge_summarizer_hf_trf.py
    # POST /cds/cds-services/discharge-summarizer
    # Docs at: http://localhost:8000/docs
"""

import os
import getpass

from dotenv import load_dotenv

from healthchain.gateway import HealthChainAPI, CDSHooksService
from healthchain.pipeline import SummarizationPipeline
from healthchain.models import CDSRequest, CDSResponse

load_dotenv()


def create_pipeline() -> SummarizationPipeline:
    if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass(
            "Enter your HuggingFace token: "
        )
    return SummarizationPipeline.from_model_id(
        "google/pegasus-xsum", source="huggingface", task="summarization"
    )


def create_app() -> HealthChainAPI:
    pipeline = create_pipeline()
    cds = CDSHooksService()

    @cds.hook("encounter-discharge", id="discharge-summarizer")
    def discharge_summarizer(request: CDSRequest) -> CDSResponse:
        return pipeline.process_request(request)

    app = HealthChainAPI(
        title="Discharge Note Summarizer",
        description="AI-powered discharge note summarization service",
        port=8000,
        service_type="cds-hooks",
    )
    app.register_service(cds, path="/cds")
    return app


app = create_app()


if __name__ == "__main__":
    import threading
    from healthchain.sandbox import SandboxClient

    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()

    client = SandboxClient(
        url="http://localhost:8000/cds/cds-services/discharge-summarizer",
        workflow="encounter-discharge",
    )
    client.load_free_text(
        csv_path="data/discharge_notes.csv",
        column_name="text",
    )
    responses = client.send_requests()
    client.save_results("./output/")

    try:
        api_thread.join()
    except KeyboardInterrupt:
        pass
