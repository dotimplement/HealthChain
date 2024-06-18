from pydantic import Field, model_validator
from healthchain.utils.idgenerator import IdGenerator

from .basehookcontext import BaseHookContext

id_generator = IdGenerator(resource_types=["Practitioner", "PractitionerRole"])


class EncounterDischargeContext(BaseHookContext):
    """
    Workflow:
    This hook is triggered during the discharge process for typically inpatient encounters. It can be invoked
    at any point from the start to the end of the discharge process. The purpose is to allow hook services to
    intervene in various aspects of the discharge decision. This includes verifying discharge medications,
    ensuring continuity of care planning, and verifying necessary documentation for discharge processing.

    Attributes:
        userId (str): REQUIRED. The ID of the current user, expected to be a Practitioner or PractitionerRole.
                      For example, 'Practitioner/123'.
        patientId (str): REQUIRED. The FHIR Patient.id of the patient being discharged.
        encounterId (str): REQUIRED. The FHIR Encounter.id of the encounter being ended.

    Documentation: https://cds-hooks.org/hooks/encounter-discharge/
    """

    userId: str = Field(
        default_factory=id_generator.generate_random_user_id,
        pattern=r"^(Practitioner|PractitionerRole)/[^\s]+$",
        description="The ID of the current user, expected to be in the format 'Practitioner/123'.",
    )
    patientId: str = Field(
        default_factory=id_generator.generate_random_patient_id,
        description="The FHIR Patient.id of the patient being discharged.",
    )
    encounterId: str = Field(
        default_factory=id_generator.generate_random_encounter_id,
        description="The FHIR Encounter.id of the encounter being ended.",
    )

    @model_validator(mode="before")
    @classmethod
    def check_unexpected_keys(cls, values):
        allowed_keys = {"userId", "patientId", "encounterId"}
        unexpected_keys = set(values) - allowed_keys
        if unexpected_keys:
            raise ValueError(f"Unexpected keys provided: {unexpected_keys}")
        return values
