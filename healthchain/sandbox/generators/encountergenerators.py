from typing import Optional
from faker import Faker

from fhir.resources.encounter import Encounter, EncounterLocation

from fhir.resources.coding import Coding
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.period import Period
from fhir.resources.reference import Reference
from healthchain.sandbox.generators.basegenerators import (
    BaseGenerator,
    generator_registry,
    register_generator,
)

from datetime import datetime


faker = Faker()


@register_generator
class PeriodGenerator(BaseGenerator):
    @staticmethod
    def generate():
        # Use date_between instead of date() for more control
        start = faker.date_between(
            start_date="-30y",  # You can adjust this range
            end_date="today",
        )
        end = faker.date_between_dates(date_start=start, date_end=datetime.now())
        return Period(
            start=start,
            end=end,
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
        generate(constraints: Optional[list] = None, random_seed: Optional[int] = None) -> Encounter:
            Generates a FHIR Encounter resource with optional constraints and random_seed.
    """

    @staticmethod
    def generate(
        constraints: Optional[list] = None,
        random_seed: Optional[int] = None,
    ) -> Encounter:
        Faker.seed(random_seed)
        patient_reference = "Patient/123"
        return Encounter(
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
            class_fhir=[generator_registry.get("ClassGenerator").generate()],
            priority=generator_registry.get("EncounterPriorityGenerator").generate(),
            type=[generator_registry.get("EncounterTypeGenerator").generate()],
            subject={"reference": patient_reference, "display": patient_reference},
            actualPeriod=generator_registry.get("PeriodGenerator").generate(),
            location=[generator_registry.get("EncounterLocationGenerator").generate()],
        )
