from pydantic import Field

from .basehookcontext import BaseHookContext


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
        ...,
        description="The ID of the current user, expected to be in the format 'Practitioner/123'.",
    )
    patientId: str = Field(
        ..., description="The FHIR Patient.id of the patient being discharged."
    )
    encounterId: str = Field(
        ..., description="The FHIR Encounter.id of the encounter being ended."
    )
