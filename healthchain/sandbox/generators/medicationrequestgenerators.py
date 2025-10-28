from typing import Optional
from faker import Faker

from healthchain.sandbox.generators.basegenerators import (
    BaseGenerator,
    generator_registry,
    register_generator,
    CodeableConceptGenerator,
)
from healthchain.sandbox.generators.value_sets.medicationcodes import (
    MedicationRequestMedication,
)
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.dosage import Dosage
from fhir.resources.reference import Reference
from fhir.resources.codeablereference import CodeableReference


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
        random_seed: Optional[int] = None,
    ):
        Faker.seed(random_seed)
        subject_reference = "Patient/123"
        encounter_reference = "Encounter/123"
        return MedicationRequest(
            resourceType="MedicationRequest",
            id=generator_registry.get("IdGenerator").generate(),
            status=generator_registry.get("EventStatusGenerator").generate(),
            intent=generator_registry.get("IntentGenerator").generate(),
            medication=CodeableReference(
                concept=generator_registry.get(
                    "MedicationRequestContainedGenerator"
                ).generate()
            ),
            subject=Reference(reference=subject_reference),
            encounter=Reference(reference=encounter_reference),
            authoredOn=generator_registry.get("DateTimeGenerator").generate(),
            dosageInstruction=[
                generator_registry.get("DosageInstructionGenerator").generate()
            ],
        )
