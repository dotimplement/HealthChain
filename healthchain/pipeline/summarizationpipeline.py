from healthchain.io.cdsfhirconnector import CdsFhirConnector
from healthchain.pipeline.base import BasePipeline
from healthchain.pipeline.components.llm import LLM


# TODO: Implement this pipeline in full
class SummarizationPipeline(BasePipeline):
    def configure_pipeline(self, model_name: str) -> None:
        cds_fhir_connector = CdsFhirConnector(hook_name="encounter-discharge")
        self.add_input(cds_fhir_connector)

        # Add summarization component
        llm = LLM(model_name)
        self.add_node(llm, stage="summarization")

        # Maybe you can have components that create cards
        # self.add_node(CardCreator(), stage="card-creation")

        self.add_output(cds_fhir_connector)
