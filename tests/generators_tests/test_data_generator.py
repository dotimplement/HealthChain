from healthchain.data_generator.data_generator import (
    DataGenerator,
)
from healthchain.base import Workflow


def test_generator_orchestrator_encounter_discharge():
    generator = DataGenerator()

    workflow = Workflow.encounter_discharge
    generator.set_workflow(workflow=workflow)
    generated_resources = generator.generate()

    assert len(generated_resources.model_dump(by_alias=True)["resources"]["entry"]) == 4


def test_generator_orchestrator_patient_view():
    generator = DataGenerator()

    workflow = Workflow.patient_view
    generator.set_workflow(workflow=workflow)
    generated_resources = generator.generate()

    assert len(generated_resources.model_dump(by_alias=True)["resources"]["entry"]) == 3