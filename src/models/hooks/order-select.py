from pydantic import Field, model_validator
from typing import List, Dict, Optional, Any, Self

from .basehookcontext import BaseHookContext


class OrderSelectContext(BaseHookContext):
    """
    Workflow: The order-select hook occurs after the clinician selects the order and before signing.
    This hook occurs when a clinician initially selects one or more new orders from a list of
    potential orders for a specific patient (including orders for medications, procedures, labs
    and other orders). The newly selected order defines that medication, procedure, lab, etc,
    but may or may not define the additional details necessary to finalize the order.

    Attributes:
        userId (str): REQUIRED. An identifier of the current user, in the format [ResourceType]/[id],
                      where ResourceType is either 'Practitioner' or 'PractitionerRole'. Examples: 'PractitionerRole/123',
                      'Practitioner/abc'.
        patientId (str): REQUIRED. The FHIR Patient.id representing the current patient in context.
        encounterId (Optional[str]): OPTIONAL. The FHIR Encounter.id representing the current encounter in context,
                                     if applicable.
        selections ([str]): REQUIRED. A list of the FHIR id(s) of the newly selected orders, referencing resources
                            in the draftOrders Bundle. Example: 'MedicationRequest/103'.
        draftOrders (object): REQUIRED. A Bundle of FHIR request resources with a draft status, representing all unsigned
                              orders from the current session, including newly selected orders.

    Documentation: https://cds-hooks.org/hooks/order-select/
    """

    # TODO: validate selection and FHIR Bundle resource

    userId: str = Field(
        pattern=r"^(Practitioner|PractitionerRole)/[^\s]+$",
        description="An identifier of the current user in the format [ResourceType]/[id].",
    )
    patientId: str = Field(
        ...,
        description="The FHIR Patient.id representing the current patient in context.",
    )
    encounterId: Optional[str] = Field(
        None,
        description="The FHIR Encounter.id of the current encounter, if applicable.",
    )
    selections: List[str] = Field(
        ..., description="A list of the FHIR ids of the newly selected orders."
    )
    draftOrders: Dict[str, Any] = Field(
        ..., description="A Bundle of FHIR request resources with a draft status."
    )

    @model_validator(mode="after")
    def validate_selections(self) -> Self:
        for selection in self.selections:
            if "/" not in selection:
                raise ValueError(
                    "Each selection must be a valid FHIR resource identifier in the format 'ResourceType/ResourceID'."
                )
        return self
