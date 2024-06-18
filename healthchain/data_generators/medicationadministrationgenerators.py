from typing import Optional
from faker import Faker

from healthchain.fhir_resources.medicationadministration import (
    MedicationAdministration,
    MedicationAdministrationDosage,
)
from healthchain.fhir_resources.generalpurpose import (
    Reference,
    CodeableReference,
)
from healthchain.fhir_resources.medicationrequest import Medication
from healthchain.data_generators.basegenerators import (
    BaseGenerator,
    generator_registry,
    register_generator,
)


faker = Faker()


@register_generator
class MedicationAdministrationDosageGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return MedicationAdministrationDosage(
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
    def generate(
        subject_reference: str,
        encounter_reference: str,
        constraints: Optional[list] = None,
    ):
        contained_medication = Medication(
            code=generator_registry.get(
                "MedicationRequestContainedGenerator"
            ).generate()
        )
        return MedicationAdministration(
            id=generator_registry.get("IdGenerator").generate(),
            status=generator_registry.get("EventStatusGenerator").generate(),
            contained=[contained_medication],
            medication=CodeableReference(
                reference=Reference(reference="Medication/123")
            ),
            subject=Reference(reference=subject_reference),
            encounter=Reference(reference=encounter_reference),
            authoredOn=generator_registry.get("DateGenerator").generate(),
            dosage=generator_registry.get(
                "MedicationAdministrationDosageGenerator"
            ).generate(),
        )
