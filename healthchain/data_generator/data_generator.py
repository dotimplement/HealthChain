from typing import List, Callable, Optional
from healthchain.fhir_resources.bundle_resources import BundleModel, Bundle_EntryModel
from healthchain.data_generator.base_generators import generator_registry
from healthchain.base import Workflow
from pydantic import BaseModel

import json


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
        self.data = []

    def fetch_generator(self, generator_name: str) -> Callable:
        return self.registry.get(generator_name)

    def set_workflow(self, workflow: str, priorities: Optional[List[str]] = None):
        self.workflow = workflow
        self.priorities = priorities

    def generate(
        self, constraints: Optional[list] = None, free_text_json: Optional[str] = None
    ) -> BaseModel:
        results = []

        if self.workflow not in self.mappings.keys():
            raise ValueError(f"Workflow {self.workflow} not found in mappings")

        if free_text_json is not None:
            with open(free_text_json) as f:
                free_text = json.load(f)
        else:
            free_text = None

        # converted_priorities = map_priorities_to_generators(priorities)
        for resource in self.mappings[self.workflow]:
            if free_text is not None:
                filtered_free_text = [
                    x
                    for x in free_text["resources"]
                    if x["resourceType"] == resource["generator"].split("Generator")[0]
                ]
            else:
                filtered_free_text = None
            generator_name = resource["generator"]
            generator = self.fetch_generator(generator_name)
            result = generator.generate(
                constraints=constraints, free_text=filtered_free_text
            )
            # print(result)
            results.append(Bundle_EntryModel(resource=result))
        output = OutputDataModel(context={}, resources=BundleModel(entry=results))
        self.data.append(output)
        return output
