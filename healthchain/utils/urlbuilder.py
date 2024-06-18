from typing import Dict

from healthchain.service.endpoints import Endpoint


class UrlBuilder:
    def __init__(self) -> None:
        self.base = ""
        self.route = ""
        self.service = ""

    @classmethod
    def build_from_config(
        cls, config: Dict[str, str], endpoints: Dict[str, Endpoint], service_id: str
    ) -> str:
        protocol = config.get("ssl_keyfile")
        if protocol is None:
            protocol = "http"
        else:
            protocol = "https"
        host = config.get("host", "127.0.0.1")
        port = config.get("port", "8000")
        service = getattr(endpoints.get("service_mount"), "path", None)
        if service is not None:
            # TODO: revisit this - not all services are formatted with id!
            service = service.format(id=service_id)
        else:
            raise ValueError(
                f"Can't fetch service details: key 'service_mount' doesn't exist in {endpoints}"
            )
        cls.base = f"{protocol}://{host}:{port}"
        cls.route = service
        cls.service = f"{protocol}://{host}:{port}{service}"

        return cls
