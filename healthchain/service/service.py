import logging
from fastapi import FastAPI

from ..base import BaseUseCase

log = logging.getLogger(__name__)


class Service:
    def __init__(self, strategy: BaseUseCase):
        self.app = FastAPI()
        self.strategy = strategy
        self.register_route()

    def register_route(self):
        for endpoint in self.strategy.endpoints.values():
            self.app.add_api_route(
                endpoint.path, endpoint.function, methods=[endpoint.method]
            )

    def run(self):
        import uvicorn

        uvicorn.run(self.app, host="127.0.0.1", port=8000)
