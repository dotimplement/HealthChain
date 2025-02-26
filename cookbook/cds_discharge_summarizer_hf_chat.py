import healthchain as hc

from healthchain.pipeline import SummarizationPipeline
from healthchain.use_cases import ClinicalDecisionSupport
from healthchain.models import CDSRequest, CDSResponse, Prefetch
from healthchain.data_generators import CdsDataGenerator

from langchain_huggingface.llms import HuggingFaceEndpoint
from langchain_huggingface import ChatHuggingFace

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

import getpass
import os


if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass("Enter your token: ")


def create_summarization_chain():
    hf = HuggingFaceEndpoint(
        repo_id="HuggingFaceH4/zephyr-7b-beta",
        task="text-generation",
        max_new_tokens=512,
        do_sample=False,
        repetition_penalty=1.03,
    )
    model = ChatHuggingFace(llm=hf)
    template = """
    You are a bed planner for a hospital. Provide a concise, objective summary of the input text in short bullet points separated by new lines,
    focusing on key actions such as appointments and medication dispense instructions, without using second or third person pronouns.\n'''{text}'''
    """
    prompt = PromptTemplate.from_template(template)
    return prompt | model | StrOutputParser()


@hc.sandbox
class DischargeNoteSummarizer(ClinicalDecisionSupport):
    def __init__(self):
        # Initialize pipeline and data generator
        chain = create_summarization_chain()
        self.pipeline = SummarizationPipeline.load(
            chain, source="langchain", template_path="templates/cds_card_template.json"
        )
        self.data_generator = CdsDataGenerator()

    @hc.ehr(workflow="encounter-discharge")
    def load_data_in_client(self) -> Prefetch:
        # Generate synthetic FHIR data for testing
        data = self.data_generator.generate_prefetch(
            free_text_path="data/discharge_notes.csv", column_name="text"
        )
        return data

    @hc.api
    def my_service(self, request: CDSRequest) -> CDSResponse:
        # Process the request through our pipeline
        result = self.pipeline(request)
        return result


if __name__ == "__main__":
    # Start the sandbox server
    summarizer = DischargeNoteSummarizer()
    summarizer.start_sandbox()
