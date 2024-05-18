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
class ClinicalStatusGenerator(BaseGenerator):
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
class VerificationStatusGenerator(BaseGenerator):
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
class CategoryGenerator(BaseGenerator):
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
class SeverityGenerator(BaseGenerator):
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
class SnomedCodeGenerator(BaseGenerator):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def generate_base():
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://snomed.info/sct",
                    code=faker.random_element(elements=("123456", "654321")),
                )
            ]
        )

    @staticmethod
    def generate_complex():
        return CodeableConceptModel(
            coding=[
                CodingModel(
                    system="http://snomed.info/sct",
                    code=faker.random_element(elements=("123456", "654321")),
                )
            ]
        )

    # @staticmethod
    def generate(self, params: Optional[dict] = None):
        if params is None:
            return self.generate_base()
        elif params.get("code") == "complex":
            return self.generate_complex()


@register_generator
class BodySiteGenerator(BaseGenerator):
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
    def generate(
        subject_reference: Optional[str],
        encounter_reference: Optional[str],
        params: Optional[dict] = None,
    ):
        subject_reference = subject_reference or "Patient/123"
        encounter_reference = encounter_reference or "Encounter/123"
        # TODO - Check whether this is the correct way to handle params
        code = generator_registry.get("SnomedCodeGenerator").generate()
        return ConditionModel(
            id=generator_registry.get("IdGenerator").generate(),
            clinicalStatus=generator_registry.get("ClinicalStatusGenerator").generate(),
            verificationStatus=generator_registry.get(
                "VerificationStatusGenerator"
            ).generate(),
            category=[generator_registry.get("CategoryGenerator").generate()],
            severity=generator_registry.get("SeverityGenerator").generate(),
            code=code,
            bodySite=[generator_registry.get("BodySiteGenerator").generate()],
            subject=ReferenceModel(reference=subject_reference),
            encounter=ReferenceModel(reference=encounter_reference),
            onsetDateTime=generator_registry.get("DateGenerator").generate(),
            abatementDateTime=generator_registry.get(
                "DateGenerator"
            ).generate(),  ## TODO: Constraint abatementDateTime to be after onsetDateTime
            recordedDate=generator_registry.get("DateGenerator").generate(),
        )
