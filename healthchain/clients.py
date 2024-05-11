import logging

from typing import Any, Callable, List, Dict

from .base import BaseUseCase, BaseClient, Workflow

log = logging.getLogger(__name__)


class EHRClient(BaseClient):
    def __init__(
        self, func: Callable[..., Any], workflow: Workflow, use_case: BaseUseCase
    ):
        """
        Initializes the EHRClient with a data generator function and optional workflow and use case.

        Parameters:
            func (Callable[..., Any]): A function to generate data for requests.
            workflow ([Workflow]): The workflow context to apply to the data generator.
            use_case ([BaseUseCase]): The strategy object to construct requests based on the generated data.
            Should be a subclass of BaseUseCase. Example - ClinicalDecisionSupport()
        """
        self.data_generator_func: Callable[..., Any] = func
        self.workflow: Workflow = workflow
        self.use_case: BaseUseCase = use_case
        self.request_data: List[Dict] = []

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
        self.request_data.append(self.use_case.construct_request(data, self.workflow))

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
        import httpx

        async with httpx.AsyncClient() as client:
            json_responses: List[Dict] = []
            for request in self.request_data:
                try:
                    response = await client.post(
                        url=url, data=request.model_dump_json(exclude_none=True)
                    )
                    json_responses.append(response.json())
                except Exception as e:
                    log.error(f"Error sending request: {e}")
                    json_responses.append({})

        return json_responses
