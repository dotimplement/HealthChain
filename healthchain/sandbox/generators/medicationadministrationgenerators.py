from typing import Optional
from faker import Faker

from fhir.resources.medicationadministration import MedicationAdministration
from fhir.resources.medicationadministration import MedicationAdministrationDosage
from fhir.resources.reference import Reference
from fhir.resources.codeablereference import CodeableReference
from healthchain.sandbox.generators.basegenerators import (
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
        return MedicationAdministration(
            id=generator_registry.get("IdGenerator").generate(),
            status=generator_registry.get("EventStatusGenerator").generate(),
            occurenceDateTime=generator_registry.get("DateGenerator").generate(),
            medication=CodeableReference(
                concept=generator_registry.get(
                    "MedicationRequestContainedGenerator"
                ).generate()
            ),
            subject=Reference(reference=subject_reference),
            encounter=Reference(reference=encounter_reference),
            dosage=generator_registry.get(
                "MedicationAdministrationDosageGenerator"
            ).generate(),
        )
