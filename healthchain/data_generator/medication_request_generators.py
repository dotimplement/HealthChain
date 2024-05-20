from healthchain.fhir_resources.medication_request_resources import (
    MedicationRequestModel,
    MedicationModel,
    DosageModel,
)
from healthchain.fhir_resources.general_purpose_resources import (
    ReferenceModel,
    CodeableReferenceModel,
)
from healthchain.data_generator.base_generators import (
    BaseGenerator,
    generate_text_field,
    generator_registry,
    register_generator,
    CodeableConceptGenerator,
)
from healthchain.data_generator.value_sets.medication import (
    MedicationRequestionMedication,
)
from typing import Optional
from faker import Faker


faker = Faker()


@register_generator
class MedicationRequestContainedGenerator(CodeableConceptGenerator):
    def generate(self, params: Optional[dict] = None):
        return self.generate_from_valueset(MedicationRequestionMedication)


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
        constraints: Optional[list] = None,
        free_text: Optional[list] = None,
    ):
        subject_reference = "Patient/123"
        encounter_reference = "Encounter/123"
        contained_medication = MedicationModel(
            code=generator_registry.get(
                "MedicationRequestContainedGenerator"
            ).generate()
        )
        text = generate_text_field(free_text)
        return MedicationRequestModel(
            id=generator_registry.get("IdGenerator").generate(),
            status=generator_registry.get("EventStatusGenerator").generate(),
            contained=[contained_medication],
            medication=CodeableReferenceModel(
                reference=ReferenceModel(reference="Medication/123")
            ),
            text=text,
            subject=ReferenceModel(reference=subject_reference),
            encounter=ReferenceModel(reference=encounter_reference),
            authoredOn=generator_registry.get("DateTimeGenerator").generate(),
            dosageInstruction=[
                generator_registry.get("DosageInstructionGenerator").generate()
            ],
        )
