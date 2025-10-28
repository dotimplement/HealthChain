import logging
import httpx
import logging.config

from functools import wraps
from typing import Any, Type, TypeVar, Optional, Callable, Union, Dict

from healthchain.sandbox.base import BaseUseCase
from healthchain.sandbox.environment import SandboxEnvironment
from healthchain.sandbox.workflows import Workflow, UseCaseType
from healthchain.sandbox.utils import (
    find_attributes_of_type,
    assign_to_attribute,
)

log = logging.getLogger(__name__)
# traceback.print_exc()

F = TypeVar("F", bound=Callable)


def is_client(attr):
    """Check if an attribute is marked as a client"""
    return hasattr(attr, "is_client")


def validate_single_registration(count, attribute_name):
    """
    Ensure only one method is registered for a role.
    Raises RuntimeError if multiple methods are registered.
    """
    if count > 1:
        raise RuntimeError(
            f"Multiple methods are registered as {attribute_name}. Only one is allowed."
        )


def register_method(instance, method, cls, name, attribute_name):
    """
    Register a method for a specific role and execute it
    """
    method_func = method.__get__(instance, cls)
    log.debug(f"Set {name} as {attribute_name}")
    return method_func()


def api(func: Optional[F] = None) -> Union[Callable[..., Any], Callable[[F], F]]:
    """
    A decorator that wraps a function in an APIMethod; this wraps a function that handles LLM/NLP
    processing and tags it as a service route to be mounted onto the main service endpoints.

    It does not take any additional arguments for now, but we may consider adding configs

    .. deprecated:: 1.0.0
        This decorator is deprecated and will be removed in a future version.
        Please use the new HealthChainAPI to create services instead.
    """
    import warnings

    warnings.warn(
        "The @api decorator is deprecated and will be removed in a future version. "
        "Please use the new HealthChainAPI to create services instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    def decorator(func: F) -> F:
        return func

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
            from healthchain.sandbox.generators import CdsDataGenerator
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
    Decorator factory for creating a sandboxed environment. The sandbox provides a controlled
    environment for testing healthcare applications by simulating EHR system interactions.
    Should be used with a use case class, such as ClinicalDocumentation or ClinicalDecisionSupport.

    Parameters:
        api: API URL as string
        config: Dictionary of configuration options

    Returns:
        A decorator function that sets up the sandbox environment for the decorated class.

    Raises:
        ValueError: If no API URL is provided or if the URL is invalid
        TypeError: If decorated class is not a valid use case

    Example:
    ```python
        # Using with API URL
        @sandbox("http://localhost:8000")
        class MyUseCase(ClinicalDocumentation):
            def __init__(self):
                super().__init__()

        # Using with config
        @sandbox(api="http://localhost:8000", config={"timeout": 30})
        class MyUseCase(ClinicalDocumentation):
            def __init__(self):
                super().__init__()
    ```
    """
    if callable(arg):
        # Decorator used without parentheses
        cls = arg
        return sandbox_decorator()(cls)
    else:
        # Arguments were provided
        api_url = None

        # Check if api was provided as a direct argument
        if isinstance(arg, str):
            api_url = arg
        # Check if api was provided in kwargs
        elif "api" in kwargs:
            api_url = kwargs["api"]

        if api_url is None:
            raise ValueError("'api' is a required argument")

        try:
            api = httpx.URL(api_url)
        except Exception as e:
            raise ValueError(f"Invalid API URL: {str(e)}")

        config = (
            kwargs.get("config", {})
            if arg is None
            else arg
            if isinstance(arg, dict)
            else {}
        )

        return sandbox_decorator(api, config)


def sandbox_decorator(
    api: Optional[Union[str, httpx.URL]] = None, config: Optional[Dict] = None
) -> Callable:
    """
    Internal decorator function that sets up a sandbox environment for a use case class.
    This function modifies the class initialization to incorporate service and client management.

    Parameters:
        api: The API URL to be used for the sandbox. Can be a string or httpx.URL object.
        config: Optional dictionary containing configurations for the sandbox environment.
               Defaults to an empty dictionary if not provided.

    Returns:
        A wrapper function that modifies the class to which it is applied, adding sandbox
        functionality including start_sandbox and stop_sandbox methods.

    Raises:
        TypeError: If the decorated class is not a subclass of BaseUseCase.
        ValueError: If the 'api' argument is not provided.
    """
    if api is None:
        raise ValueError("'api' is a required argument")

    if config is None:
        config = {}

    def wrapper(cls: Type) -> Type:
        if not issubclass(cls, BaseUseCase):
            raise TypeError(
                f"The 'sandbox' decorator can only be applied to subclasses of BaseUseCase, got {cls.__name__}"
            )

        original_init = cls.__init__

        def new_init(self, *args: Any, **kwargs: Any) -> None:
            # Initialize parent class
            super(cls, self).__init__(*args, **kwargs)
            original_init(self, *args, **kwargs)

            client_count = 0

            for name in dir(self):
                attr = getattr(self, name)
                if callable(attr):
                    # Register client
                    if is_client(attr):
                        client_count += 1
                        validate_single_registration(client_count, "_client")
                        self._client = register_method(self, attr, cls, name, "_client")

            # Initialize sandbox environment
            # TODO: Path should be passed from a config not UseCase instance
            self.sandbox_env = SandboxEnvironment(
                client=self._client,
                use_case_type=self.type,
                api=api,
                path=self.path,
                config=config,
            )

        # Replace original __init__ with new_init
        cls.__init__ = new_init

        def start_sandbox(
            self,
            service_id: Optional[str] = None,
            save_data: bool = True,
            save_dir: str = "./output/",
            logging_config: Optional[Dict] = None,
        ) -> None:
            """
            Starts the sandbox: initializes service and sends request through the client.

            Args:
                service_id: Service identifier (default None)
                save_data: Whether to save request/response data
                save_dir: Directory to save data
                logging_config: Optional logging configuration
            """
            self.sandbox_env.start_sandbox(
                service_id=service_id,
                save_data=save_data,
                save_dir=save_dir,
            )

        def stop_sandbox(self) -> None:
            """Shuts down sandbox instance"""
            self.sandbox_env.stop_sandbox()

        cls.start_sandbox = start_sandbox
        cls.stop_sandbox = stop_sandbox

        return cls

    return wrapper
