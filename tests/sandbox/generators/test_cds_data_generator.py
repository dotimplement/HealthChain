import pytest

from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.procedure import Procedure
from fhir.resources.R4B.patient import Patient

from healthchain.sandbox.generators import CdsDataGenerator
from healthchain.sandbox.workflows import Workflow


def test_generator_orchestrator_encounter_discharge():
    generator = CdsDataGenerator()

    workflow = Workflow.encounter_discharge
    generator.set_workflow(workflow=workflow)
    generator.generate_prefetch()

    assert len(generator.generated_data) == 4
    assert generator.generated_data["encounter"] is not None
    assert isinstance(generator.generated_data["encounter"], Encounter)
    assert generator.generated_data["condition"] is not None
    assert isinstance(generator.generated_data["condition"], Condition)
    assert generator.generated_data["procedure"] is not None
    assert isinstance(generator.generated_data["procedure"], Procedure)
    assert generator.generated_data["medicationrequest"] is not None


def test_generator_orchestrator_patient_view():
    generator = CdsDataGenerator()

    workflow = Workflow.patient_view
    generator.set_workflow(workflow=workflow)
    generator.generate_prefetch()

    assert len(generator.generated_data) == 3
    assert generator.generated_data["patient"] is not None
    assert isinstance(generator.generated_data["patient"], Patient)
    assert generator.generated_data["encounter"] is not None
    assert isinstance(generator.generated_data["encounter"], Encounter)
    assert generator.generated_data["condition"] is not None
    assert isinstance(generator.generated_data["condition"], Condition)


@pytest.mark.skip()
def test_generator_with_json():
    generator = CdsDataGenerator()

    workflow = Workflow.patient_view
    generator.set_workflow(workflow=workflow)
    generator.generate_prefetch(
        free_text_path="use_cases/my_encounter_data.csv", column_name="free_text"
    )

    assert len(generator.generated_data) == 4
    assert generator.generated_data["patient"] is not None
    assert generator.generated_data["encounter"] is not None
    assert generator.generated_data["condition"] is not None
    assert generator.generated_data["document"] is not None
