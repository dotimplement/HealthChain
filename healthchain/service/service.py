import logging
import uvicorn

from typing import Dict
from fastapi import FastAPI

from ..utils.endpoints import Endpoint

log = logging.getLogger(__name__)


class Service:
    def __init__(self, endpoints: Dict[str, Endpoint] = None):
        self.app = FastAPI()
        self.endpoints = endpoints

        if self.endpoints is not None:
            self.register_route()

    def register_route(self) -> None:
        # TODO: add kwargs
        for endpoint in self.endpoints.values():
            self.app.add_api_route(
                endpoint.path,
                endpoint.function,
                methods=[endpoint.method],
                response_model_exclude_none=True,
            )

    def run(self, config: Dict = None) -> None:
        if config is None:
            config = {}

        uvicorn.run(self.app, **config)
