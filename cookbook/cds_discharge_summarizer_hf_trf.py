#!/usr/bin/env python3
"""
Discharge Note Summarizer (Transformer)

CDS Hooks service that summarises discharge notes using a fine-tuned
HuggingFace transformer model (PEGASUS).

Requirements:
    pip install healthchain transformers torch python-dotenv
    # HUGGINGFACEHUB_API_TOKEN env var required
    # Note: downloads ~1GB on first run (sshleifer/distilbart-cnn-12-6)

Run:
    python cookbook/cds_discharge_summarizer_hf_trf.py
    # Fires test requests from discharge_notes.csv and exits.
    # To keep the service running for manual exploration, replace
    # `with app.sandbox(...)` with `app.run()` in the __main__ block.
"""

import os
import getpass
from pathlib import Path

from dotenv import load_dotenv

from healthchain.gateway import HealthChainAPI, CDSHooksService
from healthchain.pipeline import SummarizationPipeline
from healthchain.models import CDSRequest, CDSResponse

load_dotenv()

_DATA_DIR = Path(__file__).parent / "data"


def create_pipeline() -> SummarizationPipeline:
    if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass(
            "Enter your HuggingFace token: "
        )
    return SummarizationPipeline.from_model_id(
        "sshleifer/distilbart-cnn-12-6", source="huggingface", task="summarization"
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
        service_type="cds-hooks",
    )
    app.register_service(cds, path="/cds")
    return app


app = create_app()


if __name__ == "__main__":
    with app.sandbox("discharge-summarizer") as client:
        client.load_free_text(
            csv_path=str(_DATA_DIR / "discharge_notes.csv"),
            column_name="text",
        )
        responses = client.send_requests()
        client.save_results("./output/")
