from healthchain.data_generator.data_generator import (
    CDSDataGenerator,
)
from healthchain.base import Workflow
import pytest


def test_generator_orchestrator_encounter_discharge():
    generator = CDSDataGenerator()

    workflow = Workflow.encounter_discharge
    generator.set_workflow(workflow=workflow)
    generator.generate()

    assert len(generator.data.model_dump(by_alias=True)["prefetch"]["entry"]) == 4


def test_generator_orchestrator_patient_view():
    generator = CDSDataGenerator()

    workflow = Workflow.patient_view
    generator.set_workflow(workflow=workflow)
    generator.generate()

    assert len(generator.data.model_dump(by_alias=True)["prefetch"]["entry"]) == 3


@pytest.mark.skip()
def test_generator_with_json():
    generator = CDSDataGenerator()

    workflow = Workflow.patient_view
    generator.set_workflow(workflow=workflow)
    generator.generate(free_text_json="use_cases/example_free_text.json")

    assert len(generator.data.model_dump(by_alias=True)["prefetch"]["entry"]) == 4
