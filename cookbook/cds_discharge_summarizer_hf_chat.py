import os
import getpass

from healthchain.gateway import HealthChainAPI, CDSHooksService
from healthchain.pipeline import SummarizationPipeline
from healthchain.models import CDSRequest, CDSResponse

from langchain_huggingface.llms import HuggingFaceEndpoint
from langchain_huggingface import ChatHuggingFace
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv

load_dotenv()


if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass("Enter your token: ")


def create_summarization_chain():
    hf = HuggingFaceEndpoint(
        repo_id="deepseek-ai/DeepSeek-R1-0528",
        task="text-generation",
        max_new_tokens=512,
        do_sample=False,
        repetition_penalty=1.03,
    )

    model = ChatHuggingFace(llm=hf)

    template = """
    You are a discharge planning assistant for hospital operations.
    Provide a concise, objective summary focusing on actionable items
    for care coordination, including appointments, medications, and
    follow-up instructions. Format as bullet points with no preamble.\n'''{text}'''
    """
    prompt = PromptTemplate.from_template(template)

    return prompt | model | StrOutputParser()


# Create the healthcare application
app = HealthChainAPI(
    title="Discharge Note Summarizer",
    description="AI-powered discharge note summarization service",
)

chain = create_summarization_chain()
pipeline = SummarizationPipeline.load(
    chain, source="langchain", template_path="templates/cds_card_template.json"
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
