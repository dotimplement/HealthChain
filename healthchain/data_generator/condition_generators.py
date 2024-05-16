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
from healthchain.fhir_resources.condition_resources import (
    ConditionModel,
    Condition_StageModel,
    Condition_ParticipantModel,
)
from typing import Optional
from faker import Faker


faker = Faker()


@register_generator
class clinicalStatusGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                    code=faker.random_element(
                        elements=("active", "recurrence", "inactive", "resolved")
                    ),
                )
            ]
        )


@register_generator
class verificationStatusGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    code=faker.random_element(elements=("provisional", "confirmed")),
                )
            ]
        )


@register_generator
class categoryGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://snomed.info/sct",
                    code=faker.random_element(
                        elements=("55607006", "404684003")
                    ),  # Snomed Codes -> probably want to overwrite with template
                )
            ]
        )


@register_generator
class ConditionStageGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return Condition_StageModel(
            summary=generator_registry.get("CodeableConceptGenerator").generate(),
            assessment=generator_registry.get("ReferenceGenerator").generate(),
            type=generator_registry.get("CodeableConceptGenerator").generate(),
        )


@register_generator
class severityGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://snomed.info/sct",
                    code=faker.random_element(
                        elements=("24484000", "6736007", "255604002")
                    ),
                    # TODO: Add display values for the codes
                )
            ]
        )


@register_generator
class snomedCodeGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://snomed.info/sct",
                    code=faker.random_element(elements=("386661006")),
                    display=faker.random_element(elements=("Fever")),
                )
            ]
        )


@register_generator
class bodySiteGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://snomed.info/sct",
                    code=faker.random_element(elements=("38266002")),
                    display=faker.random_element(elements=("Entire body as a whole")),
                )
            ]
        )


@register_generator
class ConditionParticipantGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return Condition_ParticipantModel(
            type=generator_registry.get("CodeableConceptGenerator").generate(),
            individual=generator_registry.get("ReferenceGenerator").generate(),
        )


@register_generator
class ConditionModelGenerator(BaseGenerator):
    @staticmethod
    def generate(subject_reference: Optional[str], encounter_reference: Optional[str]):
        subject_reference = subject_reference or "Patient/123"
        encounter_reference = encounter_reference or "Encounter/123"
        return ConditionModel(
            id=generator_registry.get("idGenerator").generate(),
            clinicalStatus=generator_registry.get("clinicalStatusGenerator").generate(),
            verificationStatus=generator_registry.get(
                "verificationStatusGenerator"
            ).generate(),
            category=[generator_registry.get("categoryGenerator").generate()],
            severity=generator_registry.get("severityGenerator").generate(),
            code=generator_registry.get("snomedCodeGenerator").generate(),
            bodySite=[generator_registry.get("bodySiteGenerator").generate()],
            subject=ReferenceModel(reference=subject_reference),
            encounter=ReferenceModel(reference=encounter_reference),
            onsetDateTime=generator_registry.get(
                "dateGenerator"
            ).generate(),  ## Are there more plausible dates to use?
            recordedDate=generator_registry.get("dateGenerator").generate(),
        )
