import pytest

from fhir.resources.encounter import Encounter
from fhir.resources.condition import Condition
from fhir.resources.procedure import Procedure
from fhir.resources.patient import Patient

from healthchain.data_generators import CdsDataGenerator
from healthchain.sandbox.workflows import Workflow


def test_generator_orchestrator_encounter_discharge():
    generator = CdsDataGenerator()

    workflow = Workflow.encounter_discharge
    generator.set_workflow(workflow=workflow)
    generator.generate_prefetch()

    assert len(generator.generated_data.prefetch) == 4
    assert generator.generated_data.prefetch["encounter"] is not None
    assert isinstance(generator.generated_data.prefetch["encounter"], Encounter)
    assert generator.generated_data.prefetch["condition"] is not None
    assert isinstance(generator.generated_data.prefetch["condition"], Condition)
    assert generator.generated_data.prefetch["procedure"] is not None
    assert isinstance(generator.generated_data.prefetch["procedure"], Procedure)
    assert generator.generated_data.prefetch["medicationrequest"] is not None


def test_generator_orchestrator_patient_view():
    generator = CdsDataGenerator()

    workflow = Workflow.patient_view
    generator.set_workflow(workflow=workflow)
    generator.generate_prefetch()

    assert len(generator.generated_data.prefetch) == 3
    assert generator.generated_data.prefetch["patient"] is not None
    assert isinstance(generator.generated_data.prefetch["patient"], Patient)
    assert generator.generated_data.prefetch["encounter"] is not None
    assert isinstance(generator.generated_data.prefetch["encounter"], Encounter)
    assert generator.generated_data.prefetch["condition"] is not None
    assert isinstance(generator.generated_data.prefetch["condition"], Condition)


@pytest.mark.skip()
def test_generator_with_json():
    generator = CdsDataGenerator()

    workflow = Workflow.patient_view
    generator.set_workflow(workflow=workflow)
    generator.generate_prefetch(
        free_text_path="use_cases/my_encounter_data.csv", column_name="free_text"
    )

    assert len(generator.generated_data.prefetch) == 4
    assert generator.generated_data.prefetch["patient"] is not None
    assert generator.generated_data.prefetch["encounter"] is not None
    assert generator.generated_data.prefetch["condition"] is not None
    assert generator.generated_data.prefetch["document"] is not None
