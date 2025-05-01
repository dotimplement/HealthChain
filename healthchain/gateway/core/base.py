from abc import ABC, abstractmethod
from typing import Dict, Any


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


class BaseGateway(ABC):
    """Abstract base class for health system gateways"""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize gateway connection and settings"""
        pass

    @abstractmethod
    def validate_route(self, destination: str) -> bool:
        """Validate if route to destination is available"""
        pass

    @abstractmethod
    async def handle_query(self, query: Dict) -> Dict:
        """Handle synchronous query operations"""
        pass

    @abstractmethod
    async def handle_event(self, event: Dict) -> None:
        """Handle asynchronous event notifications"""
        pass

    @abstractmethod
    async def register_webhook(self, event_type: str, endpoint: str) -> str:
        """Register webhook for event notifications"""
        pass
