from abc import ABC, abstractmethod
from typing import Dict, Any
from fastapi import Request, Response


class ProtocolHandler(ABC):
    """Abstract base class for protocol handlers"""

    @abstractmethod
    async def parse_request(self, raw_request: Any) -> Dict:
        """Convert protocol-specific request to standard format"""
        pass

    @abstractmethod
    async def format_response(self, data: Dict) -> Any:
        """Convert standard response to protocol-specific format"""
        pass


class FastAPIRestHandler(ProtocolHandler):
    """REST protocol handler using FastAPI"""

    async def parse_request(self, request: Request) -> Dict:
        """Parse FastAPI request to standard format"""
        # Extract query params, headers, body
        body = (
            await request.json() if request.method in ["POST", "PUT", "PATCH"] else {}
        )
        return {
            "method": request.method,
            "path": request.url.path,
            "params": dict(request.query_params),
            "headers": dict(request.headers),
            "body": body,
        }

    async def format_response(self, data: Dict) -> Response:
        """Format standard response to FastAPI response"""
        # Convert to appropriate response format
        return data
