import random
import json

from pydantic import BaseModel
from typing import Callable, Optional

from healthchain.workflows import Workflow
from healthchain.models import CdsFhirData
from healthchain.fhir_resources.bundleresources import Bundle, BundleEntry
from healthchain.data_generators.basegenerators import generator_registry
from healthchain.fhir_resources.documentreference import DocumentReference
from healthchain.fhir_resources.generalpurpose import Narrative


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


class CdsDataGenerator:
    def __init__(self):
        self.registry = generator_registry
        self.mappings = workflow_mappings
        self.data: CdsFhirData = None

    def fetch_generator(self, generator_name: str) -> Callable:
        return self.registry.get(generator_name)

    def set_workflow(self, workflow: str):
        self.workflow = workflow

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

            results.append(BundleEntry(resource=result))

        if (
            self.workflow.value in parsed_free_text.keys()
            and parsed_free_text[self.workflow.value]
        ):
            results.append(
                BundleEntry(
                    resource=random.choice(parsed_free_text[self.workflow.value])
                )
            )
        output = CdsFhirData(prefetch=Bundle(entry=results))
        self.data = output
        return output

    def free_text_parser(self, free_text: str) -> dict:
        with open(free_text) as f:
            free_text = json.load(f)

        document_dict = {}

        for x in free_text["resources"]:
            # First parse x in to documentreferencemodel format
            text = Narrative(
                status="generated",
                div=f'<div xmlns="http://www.w3.org/1999/xhtml">{x["text"]}</div>',
            )
            doc = DocumentReference(text=text)  # TODO: Add more fields
            # if key exists append to list, otherwise initialise with list
            if x["workflow"] in document_dict.keys():
                document_dict[x["workflow"]].append(doc)
            else:
                document_dict[x["workflow"]] = [doc]

        return document_dict
