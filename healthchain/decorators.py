import logging

from functools import wraps
from typing import Any, TypeVar, Optional, Callable, Union

from .base import Workflow, BaseUseCase
from .clients import EHRClient

log = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


# TODO: add validator and error handling
def ehr(
    func: Optional[F] = None, *, workflow: Workflow, num: int = 1
) -> Union[Callable[..., Any], Callable[[F], F]]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(self: BaseUseCase, *args: Any, **kwargs: Any) -> EHRClient:
            use_case = getattr(self, "use_case", None)
            if use_case is None:
                raise ValueError(
                    f"Use case not configured! Check {type(self)} is a valid strategy."
                )

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
            return method

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)
