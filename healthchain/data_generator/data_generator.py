from typing import List, Callable, Optional
from healthchain.fhir_resources.bundle_resources import BundleModel, Bundle_EntryModel
from healthchain.data_generator.base_generators import generator_registry
from healthchain.base import Workflow
from pydantic import BaseModel


workflow_mappings = {
    Workflow.encounter_discharge: [
        {"generator": "EncounterGenerator"},
        {"generator": "ConditionGenerator"},
        {"generator": "ProcedureGenerator"},
        {"generator": "MedicationRequestGenerator"},
    ],
    Workflow.patient_view: [
        {"generator": "PatientGenerator"},
        {"generator": "EncounterGenerator"},
        {"generator": "ConditionGenerator"},
    ],
}

# TODO: Add ordering and logic so that patient/encounter IDs are passed to subsequent generators
# TODO: MAke use of value sets hard coded by tayto.
# TODO: Some of the resources should be allowed to be multiplied


class OutputDataModel(BaseModel):
    context: dict = {}
    resources: BundleModel


class DataGenerator:
    def __init__(self):
        self.registry = generator_registry
        self.mappings = workflow_mappings

    def fetch_generator(self, generator_name: str) -> Callable:
        return self.registry.get(generator_name)

    def set_workflow(self, workflow: str, priorities: Optional[List[str]] = None):
        self.workflow = workflow
        self.priorities = priorities

    def generate(self, constraints: Optional[list] = None) -> BaseModel:
        results = []

        if self.workflow not in self.mappings.keys():
            raise ValueError(f"Workflow {self.workflow} not found in mappings")

        # converted_priorities = map_priorities_to_generators(priorities)
        for resource in self.mappings[self.workflow]:
            generator_name = resource["generator"]
            generator = self.fetch_generator(generator_name)
            result = generator.generate(constraints=constraints)
            results.append(Bundle_EntryModel(resource=result))

        return OutputDataModel(context={}, resources=BundleModel(entry=results))
