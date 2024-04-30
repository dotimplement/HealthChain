from pydantic import Field
from typing import Optional

from .basehookcontext import BaseHookContext


class PatientViewContext(BaseHookContext):
    """
    Workflow: The user has just opened a patient's record; typically called only once at the beginning of a user's
    interaction with a specific patient's record.

    Attributes:
        userId (str): An identifier of the current user, in the format [ResourceType]/[id],
                      where ResourceType is one of 'Practitioner', 'PractitionerRole', 'Patient',
                      or 'RelatedPerson'. Examples: 'Practitioner/abc', 'Patient/123'.
        patientId (str): The FHIR Patient.id representing the current patient in context.
        encounterId (Optional[str]): The FHIR Encounter.id representing the current encounter in context,
                                     if applicable. This field is optional.

    Documentation: https://cds-hooks.org/hooks/patient-view/
    """

    # TODO: more comprehensive validator? for now regex should suffice

    userId: str = Field(
        pattern=r"^(Practitioner|PractitionerRole|Patient|RelatedPerson)/[^\s]+$",
        description="The ID of the current user, expected to be in the format 'Practitioner/123'.",
    )
    patientId: str = Field(..., description="The FHIR Patient.id of the patient.")
    encounterId: Optional[str] = Field(
        None, description="The FHIR Encounter.id of the encounter, if applicable."
    )
