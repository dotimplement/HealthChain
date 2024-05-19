from healthchain.data_generator.generator_orchestrator import (
    DataGenerator,
    workflow_mappings,
)
from healthchain.data_generator.base_generators import generator_registry


def test_generator_orchestrator_encounter_discharge():
    orchestrator = DataGenerator(generator_registry, workflow_mappings)

    workflow = "encounter-discharge"
    orchestrator.set_workflow(workflow=workflow)
    generated_resources = orchestrator.orchestrate()

    for resource in generated_resources:
        print(resource.model_dump_json())
    assert len(generated_resources) == 4


def test_generator_orchestrator_patient_view():
    orchestrator = DataGenerator(generator_registry, workflow_mappings)

    workflow = "patient-view"
    orchestrator.set_workflow(workflow=workflow)
    generated_resources = orchestrator.orchestrate()

    for resource in generated_resources:
        print(resource.model_dump_json())
    assert len(generated_resources) == 3
