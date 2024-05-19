from healthchain.fhir_resources.medication_administration_resources import (
    MedicationAdministrationModel,
    MedicationAdministration_DosageModel,
)
from healthchain.fhir_resources.general_purpose_resources import (
    ReferenceModel,
    CodeableReferenceModel,
)
from healthchain.data_generator.base_generators import (
    BaseGenerator,
    generator_registry,
    register_generator,
)
from healthchain.fhir_resources.medication_request_resources import MedicationModel
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
class MedicationAdministrationGenerator(BaseGenerator):
    @staticmethod
    def generate(subject_reference: str, encounter_reference: str):
        contained_medication = MedicationModel(
            code=generator_registry.get(
                "MedicationRequestContainedGenerator"
            ).generate()
        )
        return MedicationAdministrationModel(
            id=generator_registry.get("IdGenerator").generate(),
            status=generator_registry.get("EventStatusGenerator").generate(),
            contained=[contained_medication],
            medication=CodeableReferenceModel(
                reference=ReferenceModel(reference="Medication/123")
            ),
            subject=ReferenceModel(reference=subject_reference),
            encounter=ReferenceModel(reference=encounter_reference),
            authoredOn=generator_registry.get("DateGenerator").generate(),
            dosage=generator_registry.get(
                "MedicationAdministrationDosageGenerator"
            ).generate(),
        )
