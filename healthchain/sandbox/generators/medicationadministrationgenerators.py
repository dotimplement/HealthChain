from typing import Optional
from faker import Faker

from fhir.resources.R4B.medicationadministration import MedicationAdministration
from fhir.resources.R4B.medicationadministration import MedicationAdministrationDosage
from fhir.resources.R4B.reference import Reference
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
            effectiveDateTime=generator_registry.get("DateGenerator").generate(),
            medicationCodeableConcept=generator_registry.get(
                "MedicationRequestContainedGenerator"
            ).generate(),
            subject=Reference(reference=subject_reference),
            context=Reference(reference=encounter_reference),
            dosage=generator_registry.get(
                "MedicationAdministrationDosageGenerator"
            ).generate(),
        )
