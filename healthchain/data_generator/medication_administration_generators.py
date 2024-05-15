from healthchain.fhir_resources.medication_administration_resources import (
    MedicationAdministrationModel,
    MedicationAdministration_DosageModel,
)
from healthchain.fhir_resources.base_resources import ReferenceModel
from healthchain.data_generator.base_generators import (
    BaseGenerator,
    generator_registry,
    register_generator,
)
from faker import Faker


faker = Faker()


@register_generator
class MedicationAdministrationDosageGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return MedicationAdministration_DosageModel(
            text=faker.random_element(
                elements=(
                    "Take 1 tablet by mouth once daily",
                    "Take 2 tablets by mouth once daily",
                )
            ),
        )


@register_generator
class medicationAdministrationGenerator(BaseGenerator):
    @staticmethod
    def generate(subject_reference: str, encounter_reference: str):
        return MedicationAdministrationModel(
            id=generator_registry.get("idGenerator").generate(),
            status=generator_registry.get("eventStatusGenerator").generate(),
            medication=generator_registry.get("medicationGenerator").generate(),
            subject=ReferenceModel(reference=subject_reference),
            encounter=ReferenceModel(reference=encounter_reference),
            authoredOn=generator_registry.get("dateGenerator").generate(),
            dosage=generator_registry.get(
                "MedicationAdministrationDosageGenerator"
            ).generate(),
        )
