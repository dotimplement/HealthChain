import logging
import logging.config

from functools import wraps
from typing import Any, Type, TypeVar, Optional, Callable, Union, Dict

from healthchain.service import Service
from healthchain.sandbox.apimethod import APIMethod
from healthchain.sandbox.base import BaseUseCase
from healthchain.sandbox.environment import SandboxEnvironment
from healthchain.sandbox.workflows import Workflow, UseCaseType
from healthchain.sandbox.utils import (
    is_client,
    is_service_route,
    validate_single_registration,
    register_method,
    find_attributes_of_type,
    assign_to_attribute,
)

log = logging.getLogger(__name__)
# traceback.print_exc()

F = TypeVar("F", bound=Callable)


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
        def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            # Import here to avoid circular imports
            from healthchain.data_generators import CdsDataGenerator
            from healthchain.sandbox.clients.ehr import EHRClient

            # Validate function decorated is a use case base class
            assert issubclass(
                type(self), BaseUseCase
            ), f"{self.__class__.__name__} must be subclass of valid Use Case strategy!"

            # Validate workflow is a valid workflow
            try:
                workflow_enum = Workflow(workflow)
            except ValueError as e:
                raise ValueError(
                    f"{e}: please select from {[x.value for x in Workflow]}"
                )

            # Set workflow in data generator if configured
            data_generator_attributes = find_attributes_of_type(self, CdsDataGenerator)
            for i in range(len(data_generator_attributes)):
                attribute_name = data_generator_attributes[i]
                try:
                    assign_to_attribute(
                        self, attribute_name, "set_workflow", workflow_enum
                    )
                except Exception as e:
                    log.error(
                        f"Could not set workflow {workflow_enum.value} for data generator method {attribute_name}: {e}"
                    )
                if i > 1:
                    log.warning("More than one DataGenerator instances found.")

            # Wrap the function in EHRClient with workflow and strategy passed in
            if self.type in UseCaseType:
                method = EHRClient(func, workflow=workflow_enum, strategy=self.strategy)
                # Generate the number of requests specified with method
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


def sandbox(arg: Optional[Any] = None, **kwargs: Any) -> Callable:
    """
    Decorator factory for creating a sandboxed environment.

    Parameters:
        arg: Optional argument which can be a callable (class) or configuration dict.
        **kwargs: Arbitrary keyword arguments, mainly used to pass in 'service_config'.

    Returns:
        If `arg` is callable, it applies the default decorator.
        Otherwise, it uses the provided arguments to configure the service environment.

    Example:
        @sandbox(service_config={"port": 9000})
        class myCDS(ClinicalDecisionSupport):
            def __init__(self) -> None:
                self.data_generator = None
    """
    if callable(arg):
        # Decorator used without parentheses
        cls = arg
        return sandbox_decorator()(cls)
    else:
        # Arguments were provided
        if "service_config" not in kwargs:
            log.warning(
                f"{list(kwargs.keys())} is not a valid argument and will not be used; use 'service_config'."
            )
        service_config = arg if arg is not None else kwargs.get("service_config", {})

        return sandbox_decorator(service_config)


def sandbox_decorator(service_config: Optional[Dict] = None) -> Callable:
    """
    Sets up a sandbox environment. Modifies class initialization to incorporate
    service and client management.

    Parameters:
        service_config: Dictionary containing configurations for the service.

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
            # Initialize parent class
            super(cls, self).__init__(*args, **kwargs, service_config=service_config)
            original_init(self, *args, **kwargs)

            service_route_count = 0
            client_count = 0

            for name in dir(self):
                attr = getattr(self, name)
                if callable(attr):
                    # Register service API
                    if is_service_route(attr):
                        service_route_count += 1
                        validate_single_registration(
                            service_route_count, "_service_api"
                        )
                        self._service_api = register_method(
                            self, attr, cls, name, "_service_api"
                        )

                    # Register client
                    if is_client(attr):
                        client_count += 1
                        validate_single_registration(client_count, "_client")
                        self._client = register_method(self, attr, cls, name, "_client")

            # Create a Service instance and register routes from strategy
            self._service = Service(endpoints=self.endpoints)

            # Initialize sandbox environment
            self.sandbox_env = SandboxEnvironment(
                service_api=self._service_api,
                client=self._client,
                service_config=self.service_config,
                use_case_type=self.type,
                endpoints=self.endpoints,
            )

        # Replace original __init__ with new_init
        cls.__init__ = new_init

        def start_sandbox(
            self,
            service_id: str = "1",
            save_data: bool = True,
            save_dir: str = "./output/",
            logging_config: Optional[Dict] = None,
        ) -> None:
            """
            Starts the sandbox: initializes service and sends request through the client.

            Args:
                service_id: Service identifier (default "1")
                save_data: Whether to save request/response data
                save_dir: Directory to save data
                logging_config: Optional logging configuration
            """
            self.sandbox_env.start_sandbox(
                service_id=service_id,
                save_data=save_data,
                save_dir=save_dir,
                logging_config=logging_config,
            )

        def stop_sandbox(self) -> None:
            """Shuts down sandbox instance"""
            self.sandbox_env.stop_sandbox()

        cls.start_sandbox = start_sandbox
        cls.stop_sandbox = stop_sandbox

        return cls

    return wrapper
