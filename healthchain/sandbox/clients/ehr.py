import logging
from typing import Any, Callable, Dict, List, Optional

import httpx

from healthchain.models import CDSRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.sandbox.base import BaseClient, BaseRequestConstructor
from healthchain.sandbox.workflows import Workflow
from healthchain.service.endpoints import ApiProtocol

log = logging.getLogger(__name__)


class EHRClient(BaseClient):
    def __init__(
        self,
        func: Callable[..., Any],
        workflow: Workflow,
        strategy: BaseRequestConstructor,
        timeout: Optional[float] = 10.0,
    ):
        """
        Initializes the EHRClient with a data generator function and optional workflow and use case.
        Should be a subclass of BaseUseCase. Example - ClinicalDecisionSupport()

        Parameters:
            func (Callable[..., Any]): A function to generate data for requests.
            workflow ([Workflow]): The workflow context to apply to the data generator.
            strategy (BaseStrategy): The strategy object to construct requests based on the generated data.
            timeout (Optional[float], default=10.0) : The maximum time in seconds to wait for a response from the server. This parameter determines how long the client will wait before considering a request timed out.

        """
        # TODO: Add option to pass in different provider options
        self.data_generator_func: Callable[..., Any] = func
        self.workflow: Workflow = workflow
        self.strategy: BaseRequestConstructor = strategy
        self.vendor = None
        self.request_data: List[CDSRequest] = []
        self.timeout = timeout

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
            timeout = httpx.Timeout(self.timeout, read=None)
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
                        # TODO: use model_dump_json() once Pydantic V2 timezone serialization issue is resolved
                        response = await client.post(
                            url=url,
                            json=request.model_dump(exclude_none=True),
                            timeout=timeout,
                        )
                        response.raise_for_status()
                        responses.append(response.json())
                except httpx.HTTPStatusError as exc:
                    log.error(
                        f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.json()}"
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
