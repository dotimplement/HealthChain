import random
import csv
import logging

from typing import Callable, Dict, Optional, List
from pathlib import Path

from fhir.resources.resource import Resource

from healthchain.sandbox.generators.basegenerators import generator_registry
from healthchain.fhir import create_document_reference
from healthchain.sandbox.workflows import Workflow


logger = logging.getLogger(__name__)


# TODO: generate test context - move from hook models
class CdsDataGenerator:
    """
    Generates synthetic CDS (Clinical Decision Support) data for specified workflows.

    Uses registered generators to create FHIR resources (e.g., Patient, Encounter, Condition) according to workflow configuration.
    Can optionally include free text data from a CSV file as DocumentReference.

    Attributes:
        registry (dict): Maps generator names to classes.
        mappings (dict): Maps workflows to required generators.
        generated_data (Dict[str, Resource]): Most recently generated resources.
        workflow (str): Currently active workflow.

    Example:
        >>> generator = CdsDataGenerator()
        >>> generator.set_workflow("encounter_discharge")
        >>> data = generator.generate_prefetch(random_seed=42)
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
        Return the generator class by name from the registry.

        Args:
            generator_name (str): Name of the data generator.

        Returns:
            Callable: Generator class, or None if not found.

        Example:
            >>> gen = CdsDataGenerator().fetch_generator("PatientGenerator")
        """
        return self.registry.get(generator_name)

    def set_workflow(self, workflow: str) -> None:
        """
        Set the current workflow name to use for data generation.

        Args:
            workflow (str): Workflow name.
        """
        self.workflow = workflow

    def generate_prefetch(
        self,
        constraints: Optional[list] = None,
        free_text_path: Optional[str] = None,
        column_name: Optional[str] = None,
        random_seed: Optional[int] = None,
        generate_resources: bool = True,
    ) -> Dict[str, Resource]:
        """
        Generate prefetch FHIR resources and/or DocumentReference.

        Args:
            constraints (Optional[list]): Constraints for resource generation.
            free_text_path (Optional[str]): CSV file containing free text.
            column_name (Optional[str]): CSV column for free text.
            random_seed (Optional[int]): Random seed.
            generate_resources (bool): If True, generate synthetic FHIR resources.

        Returns:
            Dict[str, Resource]: Generated resources keyed by resource type (lowercase), plus "document" if a free text entry is used.

        Raises:
            ValueError: If workflow is not recognized, or column name is missing.
            FileNotFoundError: If free_text_path does not exist.
        """
        prefetch = {}

        if generate_resources:
            if self.workflow not in self.mappings:
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
        Read a column of free text from a CSV file.

        Args:
            path_to_csv (str): Path to CSV file.
            column_name (str): Column name to extract.

        Returns:
            List[str]: Extracted text values.

        Raises:
            FileNotFoundError: If CSV file does not exist.
            ValueError: If column_name is not provided.
        """
        text_data = []

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
