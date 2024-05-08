import logging
from fastapi import FastAPI
from typing import Callable

from ..utils.endpoints import Endpoint

log = logging.getLogger(__name__)


class Service:
    def __init__(self):
        self.app = FastAPI()

    def register_route(self, endpoint: Endpoint, func: Callable) -> None:
        if endpoint.service_mount:
            self.app.add_api_route(endpoint.path, func, methods=[endpoint.method])

    def run(self):
        import uvicorn

        uvicorn.run(self.app, host="127.0.0.1", port=8000)
