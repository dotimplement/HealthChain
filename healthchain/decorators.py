import logging
import threading
import asyncio

from time import sleep
from functools import wraps
from typing import Any, TypeVar, Optional, Callable, Union

from .base import BaseUseCase, Workflow, UseCaseType
from .clients import EHRClient
from .service.service import Service
from .utils.apimethod import APIMethod


log = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


# TODO: add validator and error handling
def ehr(
    func: Optional[F] = None, *, workflow: Workflow, num: int = 1
) -> Union[Callable[..., Any], Callable[[F], F]]:
    """
    A decorator that wraps around a data generator function and returns an EHRClient

    Parameters:
        func (Optional[Callable]): The function to be decorated. If None, this allows the decorator to
                                   be used with arguments.
        workflow ([str]): The workflow identifier which should match an item in the Workflow enum.
                                  This specifies the context in which the EHR function will operate.
        num (int): The number of requests to generate in the queue; defaults to 1.

    Returns:
        Callable: A decorated callable that incorporates EHR functionality or the decorator itself
                  if 'func' is None, allowing it to be used as a parameterized decorator.

    Raises:
        ValueError: If the workflow does not correspond to any defined enum or if use case is not configured.
        NotImplementedError: If the use case class is not one of the supported types.

    Example:
        @ehr(workflow='patient-view', num=2)
        def generate_data(self, config):
            # Function implementation
    """

    def decorator(func: F) -> F:
        func.is_client = True

        @wraps(func)
        def wrapper(self, *args: Any, **kwargs: Any) -> EHRClient:
            assert issubclass(
                type(self), BaseUseCase
            ), f"{self.__class__.__name__} must be subclass of valid Use Case strategy!"

            try:
                workflow_enum = Workflow(workflow)
            except ValueError as e:
                raise ValueError(
                    f"{e}: please select from {[x.value for x in Workflow]}"
                )
            if self.type in UseCaseType:
                method = EHRClient(func, workflow=workflow_enum, use_case=self)
                for _ in range(num):
                    method.generate_request(self, *args, **kwargs)
            else:
                raise NotImplementedError(
                    f"Use case {self.type} not recognised, check if implemented."
                )
            return method

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def api(func: Optional[F] = None) -> Union[Callable[..., Any], Callable[[F], F]]:
    """
    A decorator that wraps around an LLM
    """

    def decorator(func: F) -> F:
        func.is_service_route = True

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> APIMethod:
            # TODO: set any configs needed
            return APIMethod(func)

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def sandbox(cls):
    """
    A decorator function that sets up a sandbox environment. It will:
    - Initialise the use case strategy class
    - Set up a service instance
    - Trigger .send_request() function from the configured client
    """
    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        # initialse parent class, which should be a strategy use case
        super(cls, self).__init__(*args, **kwargs)
        original_init(self, *args, **kwargs)  # Call the original __init__

        for name in dir(self):
            attr = getattr(self, name)
            # Get the function decorated with @api and register it to inject in service
            if callable(attr) and hasattr(attr, "is_service_route"):
                method_func = attr.__get__(self, cls)
                self.service_api = method_func()
            # Get the function decorated with @client and asign to client
            if callable(attr) and hasattr(attr, "is_client"):
                method_func = attr.__get__(self, cls)
                # TODO: need to figure out where to pass in data spec
                self.client = method_func("123456")

        # Create a Service instance and register routes from strategy
        self.service = Service(endpoints=self.endpoints)

    cls.__init__ = new_init

    def start_sandbox(self):
        server_thread = threading.Thread(target=lambda: self.service.run())
        server_thread.start()

        sleep(5)

        # TODO: url needs to be passed in from the configs!!
        responses = asyncio.run(
            self.client.send_request(url="http://127.0.0.1:8000/cds-services/1")
        )
        print(responses)

    cls.start_sandbox = start_sandbox

    return cls
