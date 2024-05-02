import logging
import requests

from typing import Any, Callable, List, Dict

from .base import BaseUseCase, Workflow

log = logging.getLogger(__name__)


class EHRClient:
    def __init__(
        self, func: Callable[..., Any], workflow: Workflow, use_case: BaseUseCase
    ):
        self.data_generator_func: Callable[..., Any] = func
        self.workflow: Workflow = workflow
        self.use_case: BaseUseCase = use_case
        self.request_data: List[Dict] = []

    def generate_request(self, *args: Any, **kwargs: Any) -> None:
        data = self.data_generator_func(*args, **kwargs)
        self.request_data.append(self.use_case.construct_request(data, self.workflow))

    def send_request(self, url: str) -> List[Dict]:
        json_responses: List[Dict] = []
        for request in self.request_data:
            try:
                response = requests.post(
                    url=url, data=request.model_dump_json(exclude_none=True)
                )
                json_responses.append(response.json())
            except Exception as e:
                log.error(f"Error sending request: {e}")
                json_responses.append({})

        return json_responses
