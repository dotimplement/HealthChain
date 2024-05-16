import logging
import uvicorn

from typing import Dict
from fastapi import FastAPI

from ..utils.endpoints import Endpoint

log = logging.getLogger(__name__)


class Service:
    """
    A service wrapper which registers routes and starts a FastAPI service

    Parameters:
    endpoints (Dict[str, Enpoint]): the list of endpoints to register, must be a dictionary
    of Endpoint objects. Should have human-readable keys e.g. ["info", "service_mount"]

    """

    def __init__(self, endpoints: Dict[str, Endpoint] = None):
        self.app = FastAPI()
        self.endpoints = endpoints

        if self.endpoints is not None:
            self._register_routes()

    def _register_routes(self) -> None:
        # TODO: add kwargs
        for endpoint in self.endpoints.values():
            self.app.add_api_route(
                endpoint.path,
                endpoint.function,
                methods=[endpoint.method],
                response_model_exclude_none=True,
            )

    def run(self, config: Dict = None) -> None:
        """
        Starts server on uvicorn.

        Parameters:
        config (Dict): kwargs to pass into uvicorn.

        """
        if config is None:
            config = {}

        uvicorn.run(self.app, **config)
