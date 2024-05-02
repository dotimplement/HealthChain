import logging

from functools import wraps

from .base import Workflow
from .clients import EHRClient

log = logging.getLogger(__name__)


# TODO: add validator and error handling
def ehr(func=None, *, workflow=None, num=1):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            use_case = getattr(self, "use_case", None)
            if use_case is None:
                raise ValueError("Use case not configured!")

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
                method = EHRClient(func, workflow=workflow_enum, use_case=use_case)
                for _ in range(num):
                    method.generate_request(self, *args, **kwargs)
            else:
                raise NotImplementedError
            return method  # (self, *args, **kwargs)

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)
