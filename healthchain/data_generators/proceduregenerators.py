from typing import Optional
from faker import Faker

from healthchain.data_generators.basegenerators import (
    BaseGenerator,
    generator_registry,
    register_generator,
    CodeableConceptGenerator,
)
from healthchain.fhir_resources.generalpurpose import Reference
from healthchain.fhir_resources.procedure import Procedure
from healthchain.data_generators.value_sets.procedurecodes import (
    ProcedureCodeSimple,
    ProcedureCodeComplex,
)


faker = Faker()


@register_generator
class EventStatusGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return faker.random_element(elements=("in-progress", "completed"))


@register_generator
class ProcedureSnomedCodeGenerator(CodeableConceptGenerator):
    def generate(self, constraints: Optional[list] = None):
        constraints = constraints or []
        if "complex-procedure" not in constraints:
            return self.generate_from_valueset(ProcedureCodeSimple)
        elif "complex-procedure" in constraints:
            return self.generate_from_valueset(ProcedureCodeComplex)


@register_generator
class ProcedureGenerator(BaseGenerator):
    @staticmethod
    def generate(
        subject_reference: Optional[str] = None,
        encounter_reference: Optional[str] = None,
        constraints: Optional[list] = None,
    ):
        subject_reference = subject_reference or "Patient/123"
        encounter_reference = encounter_reference or "Encounter/123"
        code = generator_registry.get("ProcedureSnomedCodeGenerator").generate(
            constraints=constraints
        )
        return Procedure(
            id=generator_registry.get("IdGenerator").generate(),
            status=generator_registry.get("EventStatusGenerator").generate(),
            code=code,
            subject=Reference(reference=subject_reference),
            encounter=Reference(reference=encounter_reference),
            occurrencePeriod=generator_registry.get("PeriodGenerator").generate(),
        )
