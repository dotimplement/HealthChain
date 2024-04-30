import logging
import requests

log = logging.getLogger(__name__)


class EHRClientMethod:
    def __init__(self, func, workflow=None, use_case=None):
        self.data_generator_func = func
        self.workflow = workflow
        self.use_case = use_case
        self.request_data = []

    def generate_request(self, *args, **kwargs) -> None:
        data = self.data_generator_func(*args, **kwargs)
        self.request_data.append(self.use_case.construct_request(data, self.workflow))

    def send_request(self, url: str) -> None:
        json_responses = []
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
