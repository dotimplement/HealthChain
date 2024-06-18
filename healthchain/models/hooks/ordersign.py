from pydantic import Field, model_validator
from typing import Optional, Dict, Any
from healthchain.utils.idgenerator import IdGenerator

from .basehookcontext import BaseHookContext


id_generator = IdGenerator(resource_types=["Practitioner", "PractitionerRole"])


class OrderSignContext(BaseHookContext):
    """
    Workflow:
    The order-sign hook is triggered when a clinician is ready to sign one or more orders for a patient.
    This includes orders for medications, procedures, labs, and other orders. It is one of the last workflow
    events before an order is promoted from a draft status. The context includes all order details such as
    dose, quantity, route, etc., even though the order is still in a draft status. This hook is also applicable
    for re-signing revised orders, which may have a status other than 'draft'. The hook replaces the
    medication-prescribe and order-review hooks.

    Attributes:
        userId (str): REQUIRED. The ID of the current user, expected to be of type 'Practitioner' or 'PractitionerRole'.
                      Examples include 'PractitionerRole/123' or 'Practitioner/abc'.
        patientId (str): REQUIRED. The FHIR Patient.id representing the current patient in context.
        encounterId (Optional[str]): OPTIONAL. The FHIR Encounter.id of the current encounter in context.
        draftOrders (dict): REQUIRED. A Bundle of FHIR request resources with a draft status, representing orders that
                            aren't yet signed from the current ordering session.

    Documentation: https://cds-hooks.org/hooks/order-sign/
    """

    # TODO: validate draftOrders

    userId: str = Field(
        default_factory=id_generator.generate_random_user_id,
        pattern=r"^(Practitioner|PractitionerRole)/[^\s]+$",
        description="The ID of the current user in the format [ResourceType]/[id].",
    )
    patientId: str = Field(
        default_factory=id_generator.generate_random_patient_id,
        description="The FHIR Patient.id representing the current patient in context.",
    )
    encounterId: Optional[str] = Field(
        default_factory=id_generator.generate_random_encounter_id,
        description="The FHIR Encounter.id of the current encounter, if applicable.",
    )
    draftOrders: Dict[str, Any] = Field(
        ..., description="A Bundle of FHIR request resources with a draft status."
    )

    @model_validator(mode="before")
    @classmethod
    def check_unexpected_keys(cls, values):
        allowed_keys = {"userId", "patientId", "encounterId", "draftOrders"}
        unexpected_keys = set(values) - allowed_keys
        if unexpected_keys:
            raise ValueError(f"Unexpected keys provided: {unexpected_keys}")
        return values
