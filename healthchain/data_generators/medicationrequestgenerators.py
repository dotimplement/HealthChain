from typing import Optional
from faker import Faker

from healthchain.fhir_resources.medicationrequest import (
    MedicationRequest,
    Medication,
    Dosage,
)
from healthchain.fhir_resources.generalpurpose import (
    Reference,
    CodeableReference,
)
from healthchain.data_generators.basegenerators import (
    BaseGenerator,
    generator_registry,
    register_generator,
    CodeableConceptGenerator,
)
from healthchain.data_generators.value_sets.medicationcodes import (
    MedicationRequestMedication,
)


faker = Faker()


@register_generator
class MedicationRequestContainedGenerator(CodeableConceptGenerator):
    def generate(self):
        return self.generate_from_valueset(MedicationRequestMedication)


@register_generator
class DosageInstructionGenerator(BaseGenerator):
    @staticmethod
    def generate():
        random_int = faker.random_int(min=1, max=10)
        return Dosage(
            sequence=str(random_int),
            text=f"Take {random_int} tablet(s) by mouth once daily",
        )


@register_generator
class MedicationRequestGenerator(BaseGenerator):
    @staticmethod
    def generate(
        constraints: Optional[list] = None,
    ):
        subject_reference = "Patient/123"
        encounter_reference = "Encounter/123"
        contained_medication = Medication(
            code=generator_registry.get(
                "MedicationRequestContainedGenerator"
            ).generate()
        )
        return MedicationRequest(
            id=generator_registry.get("IdGenerator").generate(),
            status=generator_registry.get("EventStatusGenerator").generate(),
            contained=[contained_medication],
            medication=CodeableReference(
                reference=Reference(reference="Medication/123")
            ),
            subject=Reference(reference=subject_reference),
            encounter=Reference(reference=encounter_reference),
            authoredOn=generator_registry.get("DateTimeGenerator").generate(),
            dosageInstruction=[
                generator_registry.get("DosageInstructionGenerator").generate()
            ],
        )
