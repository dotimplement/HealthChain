from healthchain.data_generator.base_generators import (
    BaseGenerator,
    generator_registry,
    register_generator,
)
from healthchain.fhir_resources.general_purpose_resources import (
    CodeableConceptModel,
    CodingModel,
    ReferenceModel,
)
from healthchain.fhir_resources.procedure_resources import ProcedureModel
from typing import Optional
from faker import Faker


faker = Faker()


@register_generator
class eventStatusGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return faker.random_element(elements=("in-progress", "completed"))


@register_generator
class procedureSnomedCodeGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://snomed.info/sct",
                    code=faker.random_element(elements=("123456", "654321")),
                )
            ]
        )


@register_generator
class ProcedureModelGenerator(BaseGenerator):
    @staticmethod
    def generate(subject_reference: Optional[str], encounter_reference: Optional[str]):
        subject_reference = subject_reference or "Patient/123"
        encounter_reference = encounter_reference or "Encounter/123"
        return ProcedureModel(
            id=generator_registry.get("idGenerator").generate(),
            status=generator_registry.get("eventStatusGenerator").generate(),
            code=generator_registry.get("procedureSnomedCodeGenerator").generate(),
            subject=ReferenceModel(reference=subject_reference),
            encounter=ReferenceModel(reference=encounter_reference),
            occurrencePeriod=generator_registry.get("PeriodGenerator").generate(),
        )
