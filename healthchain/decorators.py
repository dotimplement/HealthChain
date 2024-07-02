import logging
import threading
import asyncio
import json
import uuid
import requests
import traceback

from time import sleep
from pathlib import Path
from datetime import datetime
from functools import wraps
from typing import Any, Type, TypeVar, Optional, Callable, Union, Dict

from healthchain.workflows import UseCaseType
from healthchain.apimethod import APIMethod

from .base import BaseUseCase
from .service import Service
from .utils import UrlBuilder


log = logging.getLogger(__name__)
traceback.print_exc()

F = TypeVar("F", bound=Callable)


def generate_filename(prefix: str, unique_id: str, index: int, extension: str):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    filename = f"{timestamp}_sandbox_{unique_id[:8]}_{prefix}_{index}.{extension}"
    return filename


def save_file(data, prefix, sandbox_id, index, save_dir, extension):
    save_name = generate_filename(prefix, str(sandbox_id), index, extension)
    file_path = save_dir / save_name
    if extension == "json":
        with open(file_path, "w") as outfile:
            json.dump(data, outfile, indent=4)
    elif extension == "xml":
        with open(file_path, "w") as outfile:
            outfile.write(data)


def ensure_directory_exists(directory):
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_data_to_directory(data_list, data_type, sandbox_id, save_dir, extension):
    for i, data in enumerate(data_list):
        try:
            save_file(data, data_type, sandbox_id, i, save_dir, extension)
        except Exception as e:
            log.warning(f"Error saving file {i} at {save_dir}: {e}")


def find_attributes_of_type(instance, target_type):
    attributes = []
    for attribute_name in dir(instance):
        attribute_value = getattr(instance, attribute_name)
        if isinstance(attribute_value, target_type):
            attributes.append(attribute_name)
    return attributes


def assign_to_attribute(instance, attribute_name, method_name, *args, **kwargs):
    attribute = getattr(instance, attribute_name)
    method = getattr(attribute, method_name)
    return method(*args, **kwargs)


def is_service_route(attr):
    return hasattr(attr, "is_service_route")


def is_client(attr):
    return hasattr(attr, "is_client")


def validate_single_registration(count, attribute_name):
    if count > 1:
        raise RuntimeError(
            f"Multiple methods are registered as {attribute_name}. Only one is allowed."
        )


def register_method(instance, method, cls, name, attribute_name):
    method_func = method.__get__(instance, cls)
    log.debug(f"Set {name} as {attribute_name}")
    return method_func()


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
        return sandbox_decorator()(cls)  # Apply default decorator with default settings
    else:
        # Arguments were provided, or no arguments but with parentheses
        if "service_config" not in kwargs:
            log.warning(
                f"{list(kwargs.keys())} is not a valid argument and will not be used; use 'service_config'."
            )
        service_config = arg if arg is not None else kwargs.get("service_config", {})

        return sandbox_decorator(service_config)


def sandbox_decorator(service_config: Optional[Dict] = None) -> Callable:
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
                    if is_service_route(attr):
                        service_route_count += 1
                        validate_single_registration(
                            service_route_count, "_service_api"
                        )
                        self._service_api = register_method(
                            self, attr, cls, name, "_service_api"
                        )

                    if is_client(attr):
                        client_count += 1
                        validate_single_registration(client_count, "_client")
                        self._client = register_method(self, attr, cls, name, "_client")

            # Create a Service instance and register routes from strategy
            self._service = Service(endpoints=self.endpoints)

        # Set the new init
        cls.__init__ = new_init

        def start_sandbox(
            self,
            service_id: str = "1",
            save_data: bool = True,
            save_dir: str = "./output/",
        ) -> None:
            """
            Starts the sandbox: initialises service and sends a request through the client.

            NOTE: service_id is hardcoded "1" by default, don't change.
            """
            # TODO: revisit this - default to a single service with id "1", we could have a service registry if useful
            if self._service_api is None or self._client is None:
                raise RuntimeError(
                    "Service API or Client is not configured. Please check your class initialization."
                )

            self.sandbox_id = uuid.uuid4()

            # Start service on thread
            log.info(
                f"Starting sandbox {self.sandbox_id} with {self.__class__.__name__} of type {self.type.value}..."
            )
            server_thread = threading.Thread(
                target=lambda: self._service.run(config=self.service_config)
            )
            server_thread.start()

            # Wait for service to start
            sleep(5)

            self.url = UrlBuilder.build_from_config(
                config=self.service_config,
                endpoints=self.endpoints,
                service_id=service_id,
            )

            # Send async request from client
            log.info(
                f"Sending {len(self._client.request_data)} requests generated by {self._client.__class__.__name__} to {self.url.route}"
            )

            try:
                self.responses = asyncio.run(
                    self._client.send_request(url=self.url.service)
                )
            except Exception as e:
                log.error(f"Couldn't start client: {e}")

            if save_data:
                save_dir = Path(save_dir)
                request_path = ensure_directory_exists(save_dir / "requests")
                if self.type == UseCaseType.clindoc:
                    extension = "xml"
                    save_data_to_directory(
                        [
                            request.model_dump_xml()
                            for request in self._client.request_data
                        ],
                        "request",
                        self.sandbox_id,
                        request_path,
                        extension,
                    )
                else:
                    extension = "json"
                    save_data_to_directory(
                        [
                            request.model_dump(exclude_none=True)
                            for request in self._client.request_data
                        ],
                        "request",
                        self.sandbox_id,
                        request_path,
                        extension,
                    )
                log.info(f"Saved request data at {request_path}/")

                response_path = ensure_directory_exists(save_dir / "responses")
                save_data_to_directory(
                    self.responses,
                    "response",
                    self.sandbox_id,
                    response_path,
                    extension,
                )
                log.info(f"Saved response data at {response_path}/")

        def stop_sandbox(self) -> None:
            """
            Shuts down sandbox instance
            """
            log.info("Shutting down server...")
            requests.get(self.url.base + "/shutdown")

        cls.start_sandbox = start_sandbox
        cls.stop_sandbox = stop_sandbox

        return cls

    return wrapper
