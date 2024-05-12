from healthchain.fhir_resources.encounter_resources import EncounterModel
from healthchain.fhir_resources.base_resources import CodingModel, CodeableConceptModel
from healthchain.data_generator.base_generators import BaseGenerator, generator_registry, register_generator

from faker import Faker

faker = Faker()
from typing import Optional

@register_generator
class ClassGenerator(BaseGenerator):
    @staticmethod
    def generate():
        patient_class_mapping = {
        'IMP': 'inpatient',
        'AMB': 'ambulatory'
    }
        patient_class = faker.random_element(elements=('IMP', 'AMB'))
        return CodeableConceptModel(coding=[CodingModel(
            system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
            code=patient_class,
            display=patient_class_mapping.get(patient_class)
        )]
    )


@register_generator
class EncounterTypeGenerator(BaseGenerator):
    encounter_type_mapping = {
        'ADMS': 'admission',
        'EMER': 'emergency'
    }
    encounter_type = faker.random_element(elements=('ADMS', 'EMER'))
    @staticmethod
    def generate():
        return CodeableConceptModel(coding=[CodingModel(
            system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
            code=EncounterTypeGenerator.encounter_type,
            display=EncounterTypeGenerator.encounter_type_mapping.get(EncounterTypeGenerator.encounter_type)
        )])


@register_generator
class EncounterGenerator(BaseGenerator):
    @staticmethod
    def generate(patient_reference: Optional[str]):
        if patient_reference is None:
            patient_reference = "Patient/123"
        return EncounterModel(
            resourceType="Encounter",
            id=generator_registry.get('idGenerator').generate(),
            text={
                "status": "generated",
                "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">Encounter with patient @example</div>"
            },
            # TODO: Move the elements to live with the resources
            status=faker.random_element(elements=('planned', 'in-progress', 'on-hold', 'discharged', 'cancelled')),
            class_field=[generator_registry.get('ClassGenerator').generate()],
            type_field=[generator_registry.get('EncounterTypeGenerator').generate()],
            subject={
                "reference": patient_reference,
                "display": patient_reference
            },
            participant=[],
            reason=[],
        )
