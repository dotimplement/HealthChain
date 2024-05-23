from healthchain.data_generator.base_generators import (
    BaseGenerator,
    generator_registry,
    register_generator,
    CodeableConceptGenerator,
)
from healthchain.fhir_resources.general_purpose_resources import (
    ReferenceModel,
)
from healthchain.fhir_resources.procedure_resources import ProcedureModel
from healthchain.data_generator.value_sets.procedure import (
    ProcedureCodeSimple,
    ProcedureCodeComplex,
)

from typing import Optional
from faker import Faker


faker = Faker()


@register_generator
class EventStatusGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return faker.random_element(elements=("in-progress", "completed"))


@register_generator
class ProcedureSnomedCodeGenerator(CodeableConceptGenerator):
    def generate(self, params: Optional[dict] = None):
        if params is None:
            return self.generate_from_valueset(ProcedureCodeSimple)
        elif params.get("code") == "complex":
            return self.generate_from_valueset(ProcedureCodeComplex)


@register_generator
class ProcedureGenerator(BaseGenerator):
    @staticmethod
    def generate(
        subject_reference: Optional[str] = None,
        encounter_reference: Optional[str] = None,
        constraints: Optional[list] = None,
        free_text: Optional[list] = None,
    ):
        subject_reference = subject_reference or "Patient/123"
        encounter_reference = encounter_reference or "Encounter/123"
        code = generator_registry.get("ProcedureSnomedCodeGenerator").generate()
        return ProcedureModel(
            id=generator_registry.get("IdGenerator").generate(),
            status=generator_registry.get("EventStatusGenerator").generate(),
            code=code,
            subject=ReferenceModel(reference=subject_reference),
            encounter=ReferenceModel(reference=encounter_reference),
            occurrencePeriod=generator_registry.get("PeriodGenerator").generate(),
        )
