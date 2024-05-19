from typing import List, Dict, Callable, Optional
from pydantic import BaseModel


workflow_mappings = {
    "encounter-discharge": [
        {"generator": "EncounterGenerator"},
        {"generator": "ConditionGenerator"},
        {"generator": "ProcedureGenerator"},
        {"generator": "MedicationRequestGenerator"},
    ],
    "patient-view": [
        {"generator": "PatientGenerator"},
        {"generator": "EncounterGenerator"},
        {"generator": "ConditionGenerator"},
    ],
}

# TODO: Add ordering and logic so that patient/encounter IDs are passed to subsequent generators
# TODO: MAke use of value sets hard coded by tayto.
# TODO: Some of the resources should be allowed to be multiplied


class DataGenerator:
    def __init__(
        self, registry: Dict[str, Callable], mappings: Dict[str, List[Dict[str, str]]]
    ):
        self.registry = registry
        self.mappings = mappings

    def fetch_generator(self, generator_name: str) -> Callable:
        return self.registry.get(generator_name)

    def set_workflow(self, workflow: str, priorities: Optional[List[str]] = None):
        self.workflow = workflow
        self.priorities = priorities

    def orchestrate(self) -> List[BaseModel]:
        results = []

        if self.workflow not in self.mappings.keys():
            raise ValueError(f"Workflow {self.workflow} not found in mappings")

        # converted_priorities = map_priorities_to_generators(priorities)
        for resource in self.mappings[self.workflow]:
            generator_name = resource["generator"]
            generator = self.fetch_generator(generator_name)
            result = generator.generate()
            results.append(result)

        return results
