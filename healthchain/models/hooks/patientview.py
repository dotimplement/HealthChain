from pydantic import Field, model_validator
from typing import Optional
from healthchain.utils.idgenerator import IdGenerator

from .basehookcontext import BaseHookContext


id_generator = IdGenerator(
    resource_types=["Practitioner", "PractitionerRole", "Patient", "RelatedPerson"]
)


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
        default_factory=id_generator.generate_random_user_id,
        pattern=r"^(Practitioner|PractitionerRole|Patient|RelatedPerson)/[^\s]+$",
        description="The ID of the current user, expected to be in the format 'Practitioner/123'.",
    )
    patientId: str = Field(
        default_factory=id_generator.generate_random_patient_id,
        description="The FHIR Patient.id of the patient.",
    )
    encounterId: Optional[str] = Field(
        None, description="The FHIR Encounter.id of the encounter, if applicable."
    )

    @model_validator(mode="before")
    @classmethod
    def check_unexpected_keys(cls, values):
        allowed_keys = {"userId", "patientId", "encounterId"}
        unexpected_keys = set(values) - allowed_keys
        if unexpected_keys:
            raise ValueError(f"Unexpected keys provided: {unexpected_keys}")
        return values
