import logging
import httpx

from typing import Any, Callable, List, Dict, Optional, Union, TypeVar
from functools import wraps

from healthchain.data_generators import CdsDataGenerator
from healthchain.decorators import assign_to_attribute, find_attributes_of_type
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.service.endpoints import ApiProtocol
from healthchain.workflows import UseCaseType, Workflow
from healthchain.models import CDSRequest
from healthchain.base import BaseStrategy, BaseClient, BaseUseCase

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


class EHRClient(BaseClient):
    def __init__(
        self, func: Callable[..., Any], workflow: Workflow, strategy: BaseStrategy
    ):
        """
        Initializes the EHRClient with a data generator function and optional workflow and use case.
        Should be a subclass of BaseUseCase. Example - ClinicalDecisionSupport()

        Parameters:
            func (Callable[..., Any]): A function to generate data for requests.
            workflow ([Workflow]): The workflow context to apply to the data generator.
            strategy (BaseStrategy): The strategy object to construct requests based on the generated data.

        """
        # TODO: Add option to pass in different provider options
        self.data_generator_func: Callable[..., Any] = func
        self.workflow: Workflow = workflow
        self.strategy: BaseStrategy = strategy
        self.vendor = None
        self.request_data: List[CDSRequest] = []

    def set_vendor(self, name) -> None:
        self.vendor = name

    def generate_request(self, *args: Any, **kwargs: Any) -> None:
        """
        Generates a request using the data produced by the data generator function,
        and appends it to the internal request queue.

            Parameters:
                *args (Any): Positional arguments passed to the data generator function.
                **kwargs (Any): Keyword arguments passed to the data generator function.

            Raises:
                ValueError: If the use case is not configured.
        """
        data = self.data_generator_func(*args, **kwargs)
        self.request_data.append(self.strategy.construct_request(data, self.workflow))

    async def send_request(self, url: str) -> List[Dict]:
        """
        Sends all queued requests to the specified URL and collects the responses.

            Parameters:
                url (str): The URL to which the requests will be sent.
            Returns:
                List[dict]: A list of JSON responses from the server.
            Notes:
                This method logs errors rather than raising them, to avoid interrupting the batch processing of requests.
        """
        async with httpx.AsyncClient() as client:
            responses: List[Dict] = []
            # TODO: pass timeout as config
            timeout = httpx.Timeout(10.0, read=None)
            for request in self.request_data:
                try:
                    if self.strategy.api_protocol == ApiProtocol.soap:
                        headers = {"Content-Type": "text/xml; charset=utf-8"}
                        response = await client.post(
                            url=url,
                            data=request.document,
                            headers=headers,
                            timeout=timeout,
                        )
                        response.raise_for_status()
                        response_model = CdaResponse(document=response.text)
                        responses.append(response_model.model_dump_xml())
                    else:
                        response = await client.post(
                            url=url,
                            json=request.model_dump(exclude_none=True),
                            timeout=timeout,
                        )
                        response.raise_for_status()
                        responses.append(response.json())
                except httpx.HTTPStatusError as exc:
                    log.error(
                        f"Error response {exc.response.status_code} while requesting {exc.request.url!r}."
                    )
                    responses.append({})
                except httpx.TimeoutException as exc:
                    log.error(f"Request to {exc.request.url!r} timed out!")
                    responses.append({})
                except httpx.RequestError as exc:
                    log.error(
                        f"An error occurred while requesting {exc.request.url!r}."
                    )
                    responses.append({})

        return responses
