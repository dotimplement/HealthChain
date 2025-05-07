"""
CDS Hooks protocol integration for HealthChain Gateway.

This module implements the CDS Hooks standard for clinical decision support
integration with EHR systems.
"""

from typing import Dict, List, Callable
import logging
from healthchain.gateway.core.base import InboundAdapter

logger = logging.getLogger(__name__)


class CDSHooksService(InboundAdapter):
    """
    CDS Hooks service implementation using the decorator pattern.

    CDS Hooks is an HL7 standard that allows EHR systems to request
    clinical decision support from external services at specific points
    in the clinical workflow.

    Example:
        ```python
        # Create CDS Hooks service
        cds_service = CDSHooksService(
            service_id="note-guidance",
            description="Provides clinical guidance for notes"
        )

        # Register a hook handler with decorator
        @cds_service.hook("patient-view")
        async def handle_patient_view(context, prefetch):
            # Generate cards based on patient context
            return {
                "cards": [
                    {
                        "summary": "Example guidance",
                        "indicator": "info",
                        "source": {
                            "label": "HealthChain Gateway"
                        }
                    }
                ]
            }
        ```
    """

    def __init__(self, service_id: str, description: str, **options):
        """
        Initialize a new CDS Hooks service.

        Args:
            service_id: Unique identifier for this CDS Hooks service
            description: Human-readable description of the service
            **options: Additional configuration options
        """
        super().__init__(**options)
        self.service_id = service_id
        self.description = description

    def hook(self, hook_type: str):
        """
        Decorator to register a handler for a specific CDS hook type.

        Args:
            hook_type: The CDS Hook type (e.g., "patient-view", "medication-prescribe")

        Returns:
            Decorator function that registers the handler
        """

        def decorator(handler):
            self.register_handler(hook_type, handler)
            return handler

        return decorator

    def register_handler(self, hook_type: str, handler: Callable):
        """
        Register a handler function for a specific CDS hook type.

        Args:
            hook_type: The CDS Hook type to handle
            handler: Function that will process the hook request
        """
        self._handlers[hook_type] = handler
        return self

    async def handle(self, operation: str, **params) -> Dict:
        """
        Process a CDS Hooks request using registered handlers.

        Args:
            operation: The hook type being triggered
            **params: Data for the hook, typically including:
                - context: Clinical context data
                - prefetch: Pre-fetched data from the EHR

        Returns:
            Dict containing CDS Hooks cards response
        """
        # Parse request if needed
        context = params.get("context", {})
        prefetch = params.get("prefetch", {})

        # Use registered handler if available
        if operation in self._handlers:
            cards = await self._handlers[operation](
                context=context, prefetch=prefetch, **params
            )
            return self._format_response(cards)

        # Fall back to default handler
        return await self._default_handler(operation, **params)

    async def _default_handler(self, operation: str, **params) -> Dict:
        """
        Default handler for hook types without registered handlers.

        Args:
            operation: The hook type
            **params: Additional parameters

        Returns:
            Empty CDS Hooks response
        """
        logger.warning(f"No handler registered for CDS hook type: {operation}")
        return self._format_response({"cards": []})

    def _format_response(self, response_data: Dict) -> Dict:
        """
        Format response data as CDS Hooks cards.

        Args:
            response_data: Response data containing cards

        Returns:
            Dict containing formatted CDS Hooks response
        """
        # If response already has cards key, return as is
        if "cards" in response_data:
            return response_data

        # Otherwise, wrap in cards structure
        return {"cards": response_data.get("cards", [])}

    def get_service_definition(self) -> Dict:
        """
        Get the CDS Hooks service definition for discovery.

        Returns:
            Dict containing the CDS Hooks service definition
        """
        hooks = list(self._handlers.keys())

        return {
            "services": [
                {
                    "id": self.service_id,
                    "title": self.service_id.replace("-", " ").title(),
                    "description": self.description,
                    "hook": hooks,
                }
            ]
        }

    def get_capabilities(self) -> List[str]:
        """
        Get list of supported hook operations.

        Returns:
            List of hook types this service supports
        """
        return list(self._handlers.keys())
