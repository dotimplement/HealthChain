from pydantic import Field
from typing import Optional, Dict, Any

from .basehookcontext import BaseHookContext


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
        pattern=r"^(Practitioner|PractitionerRole)/[^\s]+$",
        description="The ID of the current user in the format [ResourceType]/[id].",
    )
    patientId: str = Field(
        ...,
        description="The FHIR Patient.id representing the current patient in context.",
    )
    encounterId: Optional[str] = Field(
        None,
        description="The FHIR Encounter.id of the current encounter, if applicable.",
    )
    draftOrders: Dict[str, Any] = Field(
        ..., description="A Bundle of FHIR request resources with a draft status."
    )
