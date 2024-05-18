from healthchain.fhir_resources.medication_request_resources import (
    MedicationRequestModel,
    DosageModel,
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
from typing import Optional
from faker import Faker


faker = Faker()


@register_generator
class MedicationGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return CodeableReferenceModel(
            reference=ReferenceModel(
                reference=faker.random_element(
                    elements=("Medication/123", "Medication/456")
                )
            )
        )


@register_generator
class DosageInstructionGenerator(BaseGenerator):
    @staticmethod
    def generate():
        random_int = faker.random_int(min=1, max=10)
        return DosageModel(
            sequence=str(random_int),
            text=f"Take {random_int} tablet(s) by mouth once daily",
        )


@register_generator
class MedicationRequestGenerator(BaseGenerator):
    @staticmethod
    def generate(
        subject_reference: Optional[str] = None,
        encounter_reference: Optional[str] = None,
    ):
        subject_reference = subject_reference or "Patient/123"
        encounter_reference = encounter_reference or "Encounter/123"
        return MedicationRequestModel(
            id=generator_registry.get("IdGenerator").generate(),
            status=generator_registry.get("EventStatusGenerator").generate(),
            medication=generator_registry.get("MedicationGenerator").generate(),
            subject=ReferenceModel(reference=subject_reference),
            encounter=ReferenceModel(reference=encounter_reference),
            authoredOn=generator_registry.get("DateTimeGenerator").generate(),
            dosageInstruction=[
                generator_registry.get("DosageInstructionGenerator").generate()
            ],
        )
