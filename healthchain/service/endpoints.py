from enum import Enum
from pydantic import BaseModel, field_validator
from typing import Optional, Callable


class ApiProtocol(Enum):
    """
    Enum defining the supported API protocols.

    Available protocols:
    - soap: SOAP protocol
    - rest: REST protocol
    """

    soap = "SOAP"
    rest = "REST"


class Endpoint(BaseModel):
    path: str
    method: str
    function: Callable
    description: Optional[str] = None
    api_protocol: ApiProtocol = ApiProtocol.rest

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        method = v.upper()
        if method not in ["GET", "POST", "PUT", "DELETE"]:
            raise ValueError("Method must be 'GET', 'POST', 'PUT', or 'DELETE'.")
        return method
