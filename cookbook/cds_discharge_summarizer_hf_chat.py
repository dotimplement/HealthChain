#!/usr/bin/env python3
"""
Discharge Note Summarizer (LangChain + HuggingFace Chat)

CDS Hooks service that summarises discharge notes using a HuggingFace
chat model via LangChain (DeepSeek R1 by default).

Requirements:
    pip install healthchain langchain-core langchain-huggingface python-dotenv
    # HUGGINGFACEHUB_API_TOKEN env var required

Run:
    python cookbook/cds_discharge_summarizer_hf_chat.py
    # POST /cds/cds-services/discharge-summarizer
    # Docs at: http://localhost:8000/docs
"""

import os
import getpass

from dotenv import load_dotenv

from langchain_huggingface.llms import HuggingFaceEndpoint
from langchain_huggingface import ChatHuggingFace
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from healthchain.gateway import HealthChainAPI, CDSHooksService
from healthchain.pipeline import SummarizationPipeline
from healthchain.models import CDSRequest, CDSResponse

load_dotenv()


def create_chain():
    if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass(
            "Enter your HuggingFace token: "
        )

    hf = HuggingFaceEndpoint(
        repo_id="deepseek-ai/DeepSeek-R1-0528",
        task="text-generation",
        max_new_tokens=512,
        do_sample=False,
        repetition_penalty=1.03,
    )
    model = ChatHuggingFace(llm=hf)
    prompt = PromptTemplate.from_template(
        "You are a discharge planning assistant for hospital operations. "
        "Provide a concise, objective summary focusing on actionable items "
        "for care coordination, including appointments, medications, and "
        "follow-up instructions. Format as bullet points with no preamble.\n'''{text}'''"
    )
    return prompt | model | StrOutputParser()


def create_app() -> HealthChainAPI:
    chain = create_chain()
    pipeline = SummarizationPipeline.load(
        chain, source="langchain", template_path="templates/cds_card_template.json"
    )
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
