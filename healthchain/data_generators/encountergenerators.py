from typing import Optional
from faker import Faker

from healthchain.fhir_resources.encounter import (
    Encounter,
    EncounterLocation,
)
from healthchain.fhir_resources.primitives import dateTimeModel
from healthchain.fhir_resources.generalpurpose import (
    Coding,
    CodeableConcept,
    Period,
    Reference,
)
from healthchain.data_generators.basegenerators import (
    BaseGenerator,
    generator_registry,
    register_generator,
)


faker = Faker()


@register_generator
class PeriodGenerator(BaseGenerator):
    """
    A generator class for creating FHIR Period resources.

    Methods:
        generate() -> Period:
            Generates a FHIR Period resource with random start and end times.
    """

    @staticmethod
    def generate():
        start = faker.date_time()
        end = faker.date_time_between(start_date=start).isoformat()
        start = start.isoformat()
        return Period(
            start=dateTimeModel(start),
            end=dateTimeModel(end),
        )


@register_generator
class ClassGenerator(BaseGenerator):
    """
    A generator class for creating FHIR Class resources.

    Methods:
        generate() -> CodeableConcept:
            Generates a FHIR Class resource.
    """

    @staticmethod
    def generate() -> CodeableConcept:
        patient_class_mapping = {"IMP": "inpatient", "AMB": "ambulatory"}
        patient_class = faker.random_element(elements=("IMP", "AMB"))
        return CodeableConcept(
            coding=[
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    code=patient_class,
                    display=patient_class_mapping.get(patient_class),
                )
            ]
        )


@register_generator
class EncounterTypeGenerator(BaseGenerator):
    """
    A generator class for creating FHIR EncounterType resources.

    Methods:
        generate() -> CodeableConcept:
            Generates a FHIR EncounterType resource.
    """

    @staticmethod
    def generate() -> CodeableConcept:
        encounter_type_mapping = {"11429006": "consultation", "50849002": "emergency"}
        encounter_type = faker.random_element(elements=("11429006", "50849002"))
        return CodeableConcept(
            coding=[
                Coding(
                    system="http://snomed.info/sct",
                    code=encounter_type,
                    display=encounter_type_mapping.get(encounter_type),
                )
            ]
        )


@register_generator
class EncounterPriorityGenerator(BaseGenerator):
    """
    A generator class for creating FHIR EncounterPriority resources.

    Methods:
        generate() -> CodeableConcept:
            Generates a FHIR EncounterPriority resource.
    """

    @staticmethod
    def generate() -> CodeableConcept:
        encounter_priority_mapping = {"17621005": "normal", "24484000": "critical"}
        encounter_priority = faker.random_element(elements=("17621005", "24484000"))
        return CodeableConcept(
            coding=[
                Coding(
                    system="http://snomed.info/sct",
                    code=encounter_priority,
                    display=encounter_priority_mapping.get(encounter_priority),
                )
            ]
        )


@register_generator
class EncounterLocationGenerator(BaseGenerator):
    """
    A generator class for creating FHIR EncounterLocation resources.

    Methods:
        generate() -> EncounterLocation:
            Generates a FHIR EncounterLocation resource.
    """

    @staticmethod
    def generate() -> EncounterLocation:
        return EncounterLocation(
            location=Reference(reference="Location/123"),
            status=faker.random_element(elements=("active", "completed")),
            period=generator_registry.get("PeriodGenerator").generate(),
        )


@register_generator
class EncounterGenerator(BaseGenerator):
    """
    A generator class for creating FHIR Encounter resources.

    Methods:
        generate(constraints: Optional[list] = None) -> Encounter:
            Generates a FHIR Encounter resource with optional constraints.
    """

    @staticmethod
    def generate(
        constraints: Optional[list] = None,
    ) -> Encounter:
        patient_reference = "Patient/123"
        return Encounter(
            resourceType="Encounter",
            id=generator_registry.get("IdGenerator").generate(),
            status=faker.random_element(
                elements=(
                    "planned",
                    "in-progress",
                    "on-hold",
                    "discharged",
                    "cancelled",
                )
            ),
            class_field=[generator_registry.get("ClassGenerator").generate()],
            priority=generator_registry.get("EncounterPriorityGenerator").generate(),
            type_field=[generator_registry.get("EncounterTypeGenerator").generate()],
            subject={"reference": patient_reference, "display": patient_reference},
            actualPeriod=generator_registry.get("PeriodGenerator").generate(),
            location=[generator_registry.get("EncounterLocationGenerator").generate()],
            participant=[],
            reason=[],
        )
