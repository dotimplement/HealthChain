import logging
import threading
import asyncio

from time import sleep
from functools import wraps
from typing import Any, Type, TypeVar, Optional, Callable, Union, Dict

from .base import BaseUseCase, Workflow, UseCaseType
from .clients import EHRClient
from .service.service import Service
from .utils.apimethod import APIMethod
from .utils.urlbuilder import UrlBuilder


log = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


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
                method = EHRClient(func, workflow=workflow_enum, strategy=self.strategy)
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
    A decorator that wraps a function in an APIMethod; this wraps a function that handles LLM/NLP
    processing and tags it as a service route to be mounted onto the main service endpoints.

    It does not take any additional arguments for now, but we may consider adding configs
    """

    def decorator(func: F) -> F:
        func.is_service_route = True

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> APIMethod:
            # TODO: set any configs needed
            return APIMethod(func=func)

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def sandbox(arg: Optional[Any] = None, **kwargs: Any) -> Callable:
    """
    Decorator factory for creating a sandboxed environment, either with or without configuration.
    This can be used both as a decorator without arguments or with configuration arguments.

    Parameters:
        arg: Optional argument which can be either a callable (class) directly or a configuration dict.
        **kwargs: Arbitrary keyword arguments, mainly used to pass in 'service_config'.
        'service_config' must be a dictionary of valid kwargs to pass into uvivorn.run()

    Returns:
        If `arg` is callable, it applies the default decorator with no extra configuration.
        Otherwise, it uses the provided arguments to configure the service environment.

    Example:
    @sandbox(service_config={"port": 9000})
    class myCDS(ClinicalDecisionSupport):
        def __init__(self) -> None:
            self.data_generator = None
    """
    if callable(arg):
        # The decorator was used without parentheses, and a class was passed in directly
        cls = arg
        return decorator()(cls)  # Apply default decorator with default settings
    else:
        # Arguments were provided, or no arguments but with parentheses
        if "service_config" not in kwargs:
            log.warning(
                f"{list(kwargs.keys())} is not a valid argument and will not be used; use 'service_config'."
            )
        service_config = arg if arg is not None else kwargs.get("service_config", {})

        return decorator(service_config)


def decorator(service_config: Optional[Dict] = None) -> Callable:
    """
    A decorator function that sets up a sandbox environment. It modifies the class initialization
    to incorporate service and client management based on provided configurations. It will:

    - Initialise the use case strategy class
    - Set up a service instance
    - Trigger .send_request() function from the configured client

    Parameters:
        service_config: A dictionary containing configurations for the service.

    Returns:
        A wrapper function that modifies the class to which it is applied.
    """
    if service_config is None:
        service_config = {}

    def wrapper(cls: Type) -> Type:
        if not issubclass(cls, BaseUseCase):
            raise TypeError(
                f"The 'sandbox' decorator can only be applied to subclasses of BaseUseCase, got {cls.__name__}"
            )

        original_init = cls.__init__

        def new_init(self, *args: Any, **kwargs: Any) -> None:
            # initialse parent class, which should be a strategy use case
            super(cls, self).__init__(*args, **kwargs, service_config=service_config)
            original_init(self, *args, **kwargs)  # Call the original __init__

            service_route_count = 0
            client_count = 0

            for name in dir(self):
                attr = getattr(self, name)
                if callable(attr):
                    # Get the function decorated with @api and register it to inject in service
                    if hasattr(attr, "is_service_route"):
                        service_route_count += 1
                        if service_route_count > 1:
                            raise RuntimeError(
                                "Multiple methods are registered as service api. Only one is allowed."
                            )
                        method_func = attr.__get__(self, cls)
                        self.service_api = method_func()
                        log.debug(f"Set {name} as service_api")
                    # Get the function decorated with @client and asign to client
                    if hasattr(attr, "is_client"):
                        client_count += 1
                        if client_count > 1:
                            raise RuntimeError(
                                "Multiple methods are registered as client. Only one is allowed."
                            )
                        method_func = attr.__get__(self, cls)
                        # TODO: need to figure out where to pass in data spec
                        self.client = method_func("123456")
                        log.debug(f"Set {name} as client")

            # Create a Service instance and register routes from strategy
            self.service = Service(endpoints=self.endpoints)

        cls.__init__ = new_init

        def start_sandbox(self, service_id: str = "1") -> None:
            """
            Starts the sandbox: initialises service and sends a request through the client.

            NOTE: service_id is hardcoded "1" by default, don't change.
            """
            # TODO: revisit this - default to a single service with id "1", we could have a service resgistry if useful
            if self.service_api is None or self.client is None:
                raise RuntimeError(
                    "Service API or Client is not configured. Please check your class initialization."
                )

            # Start service on thread
            log.info(
                f"Starting {self.type.value} service {self.__class__.__name__} with configs {self.service_config}..."
            )
            server_thread = threading.Thread(
                target=lambda: self.service.run(config=self.service_config)
            )
            server_thread.start()

            # Wait for service to start
            sleep(5)

            url = UrlBuilder.build_from_config(
                config=self.service_config,
                endpoints=self.endpoints,
                service_id=service_id,
            )

            # # Send async request from client
            log.info(f"Sending {self.client.__class__.__name__} requests to {url.str}")

            try:
                self.responses = asyncio.run(self.client.send_request(url=url.str))
            except Exception as e:
                log.error(f"Couldn't start client: {e}")

        cls.start_sandbox = start_sandbox

        return cls

    return wrapper
