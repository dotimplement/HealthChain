import random
import csv
import logging

from typing import Callable, Dict, Optional, List
from pathlib import Path

from healthchain.base import Workflow
from fhir.resources.resource import Resource
from healthchain.data_generators.basegenerators import generator_registry
from healthchain.fhir import create_document_reference

logger = logging.getLogger(__name__)


# TODO: generate test context - move from hook models
class CdsDataGenerator:
    """
    A class to generate CDS (Clinical Decision Support) data based on specified workflows and constraints.

    This class provides functionality to generate synthetic FHIR resources for testing CDS systems.
    It uses registered data generators to create resources like Patients, Encounters, Conditions etc.
    based on configured workflows. It can also incorporate free text data from CSV files.

    Attributes:
        registry (dict): A registry mapping generator names to generator classes.
        mappings (dict): A mapping of workflow names to lists of required generators.
        generated_data (Dict[str, Resource]): The most recently generated FHIR resources.
        workflow (str): The currently active workflow.

    Example:
        >>> generator = CdsDataGenerator()
        >>> generator.set_workflow("encounter_discharge")
        >>> data = generator.generate_prefetch(
        ...     random_seed=42
        ... )
    """

    # TODO: Add ordering and logic so that patient/encounter IDs are passed to subsequent generators
    # TODO: Some of the resources should be allowed to be multiplied

    default_workflow_mappings = {
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

    def __init__(self):
        self.registry = generator_registry
        self.mappings = self.default_workflow_mappings
        self.generated_data: Dict[str, Resource] = {}

    def fetch_generator(self, generator_name: str) -> Callable:
        """
        Fetches a data generator class by its name from the registry.

        Args:
            generator_name (str): The name of the data generator to fetch (e.g. "PatientGenerator", "EncounterGenerator")

        Returns:
            Callable: The data generator class that can be used to generate FHIR resources. Returns None if generator not found.

        Example:
            >>> generator = CdsDataGenerator()
            >>> patient_gen = generator.fetch_generator("PatientGenerator")
            >>> patient = patient_gen.generate()
        """
        return self.registry.get(generator_name)

    def set_workflow(self, workflow: str) -> None:
        """
        Sets the current workflow to be used for data generation.

        Parameters:
            workflow (str): The name of the workflow to set.
        """
        self.workflow = workflow

    def generate_prefetch(
        self,
        constraints: Optional[list] = None,
        free_text_path: Optional[str] = None,
        column_name: Optional[str] = None,
        random_seed: Optional[int] = None,
    ) -> Dict[str, Resource]:
        """
        Generates CDS data based on the current workflow, constraints, and optional free text data.

        This method generates FHIR resources according to the configured workflow mapping. For each
        resource type in the workflow, it uses the corresponding generator to create a FHIR resource.
        If free text data is provided via CSV, it will also generate a DocumentReference containing
        randomly selected text from the CSV.

        Args:
            constraints (Optional[list]): A list of constraints to apply to the data generation.
                Each constraint should match the format expected by the individual generators.
            free_text_path (Optional[str]): Path to a CSV file containing free text data to be
                included as DocumentReferences. If provided, column_name must also be specified.
            column_name (Optional[str]): The name of the column in the CSV file containing the
                free text data to use. Required if free_text_path is provided.
            random_seed (Optional[int]): Seed value for random number generation to ensure
                reproducible results. If not provided, generation will be truly random.

        Returns:
            Dict[str, Resource]: A dictionary mapping resource types to generated FHIR resources.
                The keys are lowercase resource type names (e.g. "patient", "encounter").
                If free text is provided, includes a "document" key with a DocumentReference.

        Raises:
            ValueError: If the configured workflow is not found in the mappings
            FileNotFoundError: If the free_text_path is provided but file not found
            ValueError: If free_text_path provided without column_name
        """
        prefetch = {}

        if self.workflow not in self.mappings.keys():
            raise ValueError(f"Workflow {self.workflow} not found in mappings")

        for resource in self.mappings[self.workflow]:
            generator_name = resource["generator"]
            generator = self.fetch_generator(generator_name)
            resource = generator.generate(
                constraints=constraints, random_seed=random_seed
            )

            prefetch[resource.__resource_type__.lower()] = resource

        parsed_free_text = (
            self.free_text_parser(free_text_path, column_name)
            if free_text_path
            else None
        )
        if parsed_free_text:
            prefetch["document"] = create_document_reference(
                data=random.choice(parsed_free_text),
                content_type="text/plain",
                status="current",
                description="Free text created by HealthChain CdsDataGenerator",
                attachment_title="Free text created by HealthChain CdsDataGenerator",
            )

        self.generated_data = prefetch

        return self.generated_data

    def free_text_parser(self, path_to_csv: str, column_name: str) -> List[str]:
        """
        Parse free text data from a CSV file.

        This method reads a CSV file and extracts text data from a specified column. The text data
        can later be used to create DocumentReference resources.

        Args:
            path_to_csv (str): Path to the CSV file containing the free text data.
            column_name (str): Name of the column in the CSV file to extract text from.

        Returns:
            List[str]: List of text strings extracted from the specified column.

        Raises:
            FileNotFoundError: If the specified CSV file does not exist or is not a file.
            ValueError: If column_name is not provided.
            Exception: If any other error occurs while reading/parsing the CSV file.
        """
        text_data = []

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
                        text_data.append(row[column_name])
                else:
                    raise ValueError(
                        "Column name must be provided when header is True."
                    )
        except Exception as ex:
            logger.error(f"An error occurred: {ex}")

        return text_data
