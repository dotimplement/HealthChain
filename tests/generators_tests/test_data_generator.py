from healthchain.data_generator.data_generator import (
    DataGenerator,
)
from healthchain.base import Workflow
import pytest


def test_generator_orchestrator_encounter_discharge():
    generator = DataGenerator()

    workflow = Workflow.encounter_discharge
    generator.set_workflow(workflow=workflow)
    generator.generate()

    assert len(generator.data.model_dump(by_alias=True)["resources"]["entry"]) == 4


def test_generator_orchestrator_patient_view():
    generator = DataGenerator()

    workflow = Workflow.patient_view
    generator.set_workflow(workflow=workflow)
    generator.generate()

    assert len(generator.data.model_dump(by_alias=True)["resources"]["entry"]) == 3


@pytest.mark.skip()
def test_generator_with_json():
    generator = DataGenerator()

    workflow = Workflow.patient_view
    generator.set_workflow(workflow=workflow)
    generator.generate(
        free_text_path="use_cases/my_encounter_data.csv", column_name="free_text"
    )

    assert len(generator.data.model_dump(by_alias=True)["resources"]["entry"]) == 4
