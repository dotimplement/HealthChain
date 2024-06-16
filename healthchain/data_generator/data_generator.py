from typing import Callable, Optional
from healthchain.fhir_resources.bundle_resources import BundleModel, Bundle_EntryModel
from healthchain.data_generator.base_generators import generator_registry
from healthchain.fhir_resources.document_reference_resources import (
    DocumentReferenceModel,
)
from healthchain.fhir_resources.general_purpose_resources import NarrativeModel
from healthchain.base import Workflow
from pydantic import BaseModel
from pathlib import Path


import random
import csv

import logging

logger = logging.getLogger(__name__)


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

    def set_workflow(self, workflow: str):
        self.workflow = workflow

    def generate(
        self,
        constraints: Optional[list] = None,
        free_text_path: Optional[str] = None,
        column_name: Optional[str] = None,
    ) -> BaseModel:
        results = []

        if self.workflow not in self.mappings.keys():
            raise ValueError(f"Workflow {self.workflow} not found in mappings")

        for resource in self.mappings[self.workflow]:
            generator_name = resource["generator"]
            generator = self.fetch_generator(generator_name)
            result = generator.generate(constraints=constraints)

            results.append(Bundle_EntryModel(resource=result))

        parsed_free_text = (
            self.free_text_parser(free_text_path, column_name)
            if free_text_path
            else None
        )
        if parsed_free_text:
            results.append(Bundle_EntryModel(resource=random.choice(parsed_free_text)))
        output = OutputDataModel(context={}, resources=BundleModel(entry=results))
        self.data = output
        return output

    def free_text_parser(self, path_to_csv: str, column_name: str) -> dict:
        column_data = []

        # Check that path_to_csv is a valid path with pathlib
        path = Path(path_to_csv)
        if not path.is_file():
            raise FileNotFoundError(
                f"The file {path_to_csv} does not exist or is not a file."
            )

        try:
            with path.open(mode="r", newline="") as file:
                reader = csv.DictReader(file)
                if column_name is not None:
                    for row in reader:
                        column_data.append(row[column_name])
                else:
                    raise ValueError(
                        "Column name must be provided when header is True."
                    )
        except Exception as ex:
            logger.error(f"An error occurred: {ex}")

        document_list = []

        for x in column_data:
            # First parse x in to documentreferencemodel format
            text = NarrativeModel(
                status="generated",
                div=f'<div xmlns="http://www.w3.org/1999/xhtml">{x}</div>',
            )
            doc = DocumentReferenceModel(text=text)
            document_list.append(doc)

        return document_list
