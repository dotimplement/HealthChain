from healthchain.data_generator.generator_orchestrator import (
    GeneratorOrchestrator,
    workflow_mappings,
)
from healthchain.data_generator.base_generators import generator_registry


def test_generator_orchestrator_encounter_discharge():
    orchestrator = GeneratorOrchestrator(generator_registry, workflow_mappings)

    workflow = "encounter-discharge"
    generated_resources = orchestrator.orchestrate(workflow=workflow)

    for resource in generated_resources:
        print(resource.model_dump_json())
    assert len(generated_resources) == 4


def test_generator_orchestrator_patient_view():
    orchestrator = GeneratorOrchestrator(generator_registry, workflow_mappings)

    workflow = "patient-view"
    generated_resources = orchestrator.orchestrate(workflow=workflow)

    for resource in generated_resources:
        print(resource.model_dump_json())
    assert len(generated_resources) == 3
