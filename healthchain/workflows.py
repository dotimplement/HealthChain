from enum import Enum


class UseCaseType(Enum):
    cds = "ClinicalDecisionSupport"
    clindoc = "ClinicalDocumentation"


# a workflow is a specific event that may occur in an EHR that triggers a request to server
class Workflow(Enum):
    patient_view = "patient-view"
    order_select = "order-select"
    order_sign = "order-sign"
    encounter_discharge = "encounter-discharge"
    sign_note_inpatient = "sign-note-inpatient"
    sign_note_outpatient = "sign-note-outpatient"


class UseCaseMapping(Enum):
    ClinicalDecisionSupport = (
        "patient-view",
        "order-select",
        "order-sign",
        "encounter-discharge",
    )
    ClinicalDocumentation = ("sign-note-inpatient", "sign-note-outpatient")

    def __init__(self, *workflows):
        self.allowed_workflows = workflows


def is_valid_workflow(use_case: UseCaseMapping, workflow: Workflow) -> bool:
    return workflow.value in use_case.allowed_workflows


def validate_workflow(use_case: UseCaseMapping):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if len(kwargs) > 0:
                workflow = kwargs.get("workflow")
            else:
                for arg in args:
                    if type(arg) == Workflow:
                        workflow = arg
            if not is_valid_workflow(use_case, workflow):
                raise ValueError(f"Invalid workflow {workflow} for UseCase {use_case}")
            return func(*args, **kwargs)

        return wrapper

    return decorator
