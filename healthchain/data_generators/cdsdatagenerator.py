import random
import csv
import logging

from pydantic import BaseModel
from typing import Callable, Dict, Optional
from pathlib import Path

from healthchain.base import Workflow
from healthchain.fhir_resources.bundleresources import Bundle, BundleEntry
from healthchain.data_generators.basegenerators import generator_registry
from healthchain.fhir_resources.documentreference import DocumentReference
from healthchain.fhir_resources.generalpurpose import Narrative
from healthchain.models.data.cdsfhirdata import CdsFhirData

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


class CdsDataGenerator:
    """
    A class to generate CDS (Clinical Decision Support) data based on specified workflows and constraints.

    Attributes:
        registry (dict): A registry of data generators.
        mappings (dict): A mapping of workflows to their respective data generators.
        data (CdsFhirData): The generated CDS FHIR data.
    """

    def __init__(self):
        self.registry = generator_registry
        self.mappings = workflow_mappings
        self.data: CdsFhirData = None

    def fetch_generator(self, generator_name: str) -> Callable:
        """
        Fetches a data generator function by its name from the registry.

        Parameters:
            generator_name (str): The name of the data generator to fetch.

        Returns:
            Callable: The data generator function.
        """
        return self.registry.get(generator_name)

    def set_workflow(self, workflow: str) -> None:
        """
        Sets the current workflow to be used for data generation.

        Parameters:
            workflow (str): The name of the workflow to set.
        """
        self.workflow = workflow

    def generate(
        self,
        constraints: Optional[list] = None,
        free_text_path: Optional[str] = None,
        column_name: Optional[str] = None,
    ) -> BaseModel:
        """
        Generates CDS data based on the current workflow, constraints, and optional free text data.

        Parameters:
            constraints (Optional[list]): A list of constraints to apply to the data generation.
            free_text_path (Optional[str]): The path to a CSV file containing free text data.
            column_name (Optional[str]): The column name in the CSV file to use for free text data.

        Returns:
            BaseModel: The generated CDS FHIR data.
        """
        results = []

        if self.workflow not in self.mappings.keys():
            raise ValueError(f"Workflow {self.workflow} not found in mappings")

        for resource in self.mappings[self.workflow]:
            generator_name = resource["generator"]
            generator = self.fetch_generator(generator_name)
            result = generator.generate(constraints=constraints)

            results.append(BundleEntry(resource=result))

        parsed_free_text = (
            self.free_text_parser(free_text_path, column_name)
            if free_text_path
            else None
        )
        if parsed_free_text:
            results.append(BundleEntry(resource=random.choice(parsed_free_text)))

        output = CdsFhirData(prefetch=Bundle(entry=results))
        self.data = output
        return output

    def free_text_parser(self, path_to_csv: str, column_name: str) -> Dict:
        """
        Parses free text data from a CSV file and converts it into a list of DocumentReference models.

        Parameters:
            path_to_csv (str): The path to the CSV file containing free text data.
            column_name (str): The column name in the CSV file to use for free text data.

        Returns:
            dict: A dictionary of parsed free text data converted into DocumentReference models.
        """
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
            text = Narrative(
                status="generated",
                div=f'<div xmlns="http://www.w3.org/1999/xhtml">{x}</div>',
            )
            doc = DocumentReference(text=text)
            document_list.append(doc)

        return document_list
