from healthchain.fhir_resources.encounter_resources import EncounterModel
from healthchain.fhir_resources.base_resources import CodingModel, CodeableConceptModel
from healthchain.data_generator.base_generators import (
    BaseGenerator,
    generator_registry,
    register_generator,
)
from typing import Optional
from faker import Faker

faker = Faker()


@register_generator
class ClassGenerator(BaseGenerator):
    @staticmethod
    def generate():
        patient_class_mapping = {"IMP": "inpatient", "AMB": "ambulatory"}
        patient_class = faker.random_element(elements=("IMP", "AMB"))
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    code=patient_class,
                    display=patient_class_mapping.get(patient_class),
                )
            ]
        )


@register_generator
class EncounterTypeGenerator(BaseGenerator):
    @staticmethod
    def generate():
        encounter_type_mapping = {"11429006": "consultation", "50849002": "emergency"}
        encounter_type = faker.random_element(elements=("11429006", "50849002"))
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://snomed.info/sct",
                    code=encounter_type,
                    display=encounter_type_mapping.get(encounter_type),
                )
            ]
        )


@register_generator
class EncounterPriorityGenerator(BaseGenerator):
    @staticmethod
    def generate():
        encounter_priority_mapping = {"17621005": "normal", "24484000": "critical"}
        encounter_priority = faker.random_element(elements=("17621005", "24484000"))
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://snomed.info/sct",
                    code=encounter_priority,
                    display=encounter_priority_mapping.get(encounter_priority),
                )
            ]
        )


@register_generator
class EncounterGenerator(BaseGenerator):
    @staticmethod
    def generate(patient_reference: Optional[str]):
        if patient_reference is None:
            patient_reference = "Patient/123"
        return EncounterModel(
            resourceType="Encounter",
            id=generator_registry.get("idGenerator").generate(),
            text={
                "status": "generated",
                "div": '<div xmlns="http://www.w3.org/1999/xhtml">Encounter with patient @example</div>',
            },
            status=faker.random_element(
                elements=(
                    "planned",
                    "in-progress",
                    "on-hold",
                    "discharged",
                    "cancelled",
                )
            ),
            class_field=[generator_registry.get("ClassGenerator").generate()],
            type_field=[generator_registry.get("EncounterTypeGenerator").generate()],
            subject={"reference": patient_reference, "display": patient_reference},
            participant=[],
            reason=[],
        )
