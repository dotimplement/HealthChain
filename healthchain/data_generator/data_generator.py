from typing import List, Callable, Optional
from healthchain.fhir_resources.bundle_resources import BundleModel, Bundle_EntryModel
from healthchain.data_generator.base_generators import generator_registry
from healthchain.fhir_resources.document_reference_resources import (
    DocumentReferenceModel,
)
from healthchain.fhir_resources.general_purpose_resources import NarrativeModel
from healthchain.base import Workflow
from pydantic import BaseModel

import random
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
            parsed_free_text = self.free_text_parser(free_text_json)
        else:
            parsed_free_text = {self.workflow.value: []}

        for resource in self.mappings[self.workflow]:
            generator_name = resource["generator"]
            generator = self.fetch_generator(generator_name)
            result = generator.generate(constraints=constraints)

            results.append(Bundle_EntryModel(resource=result))

        print("############################")
        print(self.workflow.value)
        print(parsed_free_text.keys())
        print(self.workflow.value in parsed_free_text.keys())
        if (
            self.workflow.value in parsed_free_text.keys()
            and parsed_free_text[self.workflow.value]
        ):
            results.append(
                Bundle_EntryModel(
                    resource=random.choice(parsed_free_text[self.workflow.value])
                )
            )
        output = OutputDataModel(context={}, resources=BundleModel(entry=results))
        self.data = output
        return output

    def free_text_parser(self, free_text: str) -> dict:
        with open(free_text) as f:
            free_text = json.load(f)

        document_dict = {}

        for x in free_text["resources"]:
            # First parse x in to documentreferencemodel format
            text = NarrativeModel(
                status="generated",
                div=f'<div xmlns="http://www.w3.org/1999/xhtml">{x["text"]}</div>',
            )
            doc = DocumentReferenceModel(text=text)  # TODO: Add more fields
            # if key exists append to list, otherwise initialise with list
            if x["workflow"] in document_dict.keys():
                document_dict[x["workflow"]].append(doc)
            else:
                document_dict[x["workflow"]] = [doc]

        return document_dict
