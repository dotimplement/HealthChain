import logging

from functools import wraps

from .base import Workflow
from .methods import EHRClientMethod

log = logging.getLogger(__name__)


def ehr(func=None, *, workflow=None, use_case=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                workflow_enum = Workflow(workflow)
            except ValueError as e:
                raise ValueError(
                    f"{e}: please select from {[x.value for x in Workflow]}"
                )

            if use_case.__class__.__name__ in [
                "ClinicalDocumentation",
                "ClinicalDecisionSupport",
            ]:
                method = EHRClientMethod(
                    func, workflow=workflow_enum, use_case=use_case
                )
            else:
                raise NotImplementedError
            return method(*args, **kwargs)

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)
