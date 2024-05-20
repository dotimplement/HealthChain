from contextlib import asynccontextmanager
import os
import signal
import logging
import uvicorn

from typing import Dict
from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from termcolor import colored

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
        self.app = FastAPI(lifespan=self.lifespan)
        self.endpoints = endpoints
        self.dashboard_url = "/dashboard"

        if self.endpoints is not None:
            self._register_routes()

        # Router to handle stopping the server
        self.stop_router = APIRouter()
        self.stop_router.add_api_route("/shutdown", self._shutdown, methods=["GET"])
        self.app.include_router(self.stop_router)

    def _register_routes(self) -> None:
        # TODO: add kwargs
        for endpoint in self.endpoints.values():
            self.app.add_api_route(
                endpoint.path,
                endpoint.function,
                methods=[endpoint.method],
                response_model_exclude_none=True,
            )

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        self._startup()
        yield
        self._shutdown()

    def _startup(self) -> None:
        healthchain_ascii = r"""

    __  __           ____  __    ________          _
   / / / /__  ____ _/ / /_/ /_  / ____/ /_  ____ _(_)___
  / /_/ / _ \/ __ `/ / __/ __ \/ /   / __ \/ __ `/ / __ \
 / __  /  __/ /_/ / / /_/ / / / /___/ / / / /_/ / / / / /
/_/ /_/\___/\__,_/_/\__/_/ /_/\____/_/ /_/\__,_/_/_/ /_/

"""  # noqa: E501

        colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]
        for i, line in enumerate(healthchain_ascii.split("\n")):
            color = colors[i % len(colors)]
            print(colored(line, color))
        # print(healthchain_ascii)
        for endpoint in self.endpoints.values():
            print(
                f"{colored('HEALTHCHAIN', 'green')}: {endpoint.method} endpoint at {endpoint.path}/"
            )
        print(
            f"{colored('HEALTHCHAIN', 'green')}: See more details at {colored(self.app.docs_url, 'magenta')}"
        )
        print(
            f"{colored('HEALTHCHAIN', 'green')}: Interact with sandbox at {colored(self.dashboard_url, 'magenta')}"
        )

    def _shutdown(self):
        """
        Shuts down server
        """
        os.kill(os.getpid(), signal.SIGTERM)
        return JSONResponse(content={"message": "Server is shutting down..."})

    def run(self, config: Dict = None) -> None:
        """
        Starts server on uvicorn.

        Parameters:
        config (Dict): kwargs to pass into uvicorn.

        """
        if config is None:
            config = {}

        uvicorn.run(self.app, **config)
