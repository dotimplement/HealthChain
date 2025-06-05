from enum import Enum
from pydantic import BaseModel, field_validator
from typing import Optional, Callable
import warnings


# Keep for backward compatibility but warn about new location
try:
    from healthchain.gateway.protocols.apiprotocol import ApiProtocol
except ImportError:
    # Fallback definition if the new location isn't available yet
    class ApiProtocol(Enum):
        """
        DEPRECATED: This enum has moved to healthchain.gateway.protocols.api_protocol
        """

        soap = "SOAP"
        rest = "REST"

        def __init__(self, *args, **kwargs):
            warnings.warn(
                "ApiProtocol has moved to healthchain.gateway.protocols.api_protocol. "
                "This location is deprecated and will be removed in a future version.",
                DeprecationWarning,
                stacklevel=2,
            )
            super().__init__(*args, **kwargs)


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
