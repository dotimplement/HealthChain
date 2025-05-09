"""
FHIR client connector for HealthChain Gateway.

This module provides FHIR client functionality to connect to and interact with
external FHIR servers through a consistent interface.
"""

from typing import List, Any
import logging
import aiohttp

from healthchain.gateway.core.base import OutboundAdapter

try:
    import fhirclient.client as fhir_client
except ImportError:
    fhir_client = None

logger = logging.getLogger(__name__)


class FHIRClient(OutboundAdapter):
    """
    FHIR client implementation using the decorator pattern.

    Provides a client to connect with external FHIR servers and
    makes outbound requests using a clean decorator-based API.

    Example:
        ```python
        # Create FHIR client
        fhir_client = FHIRClient(base_url="https://r4.smarthealthit.org")

        # Register a custom operation handler
        @fhir_client.operation("patient_search")
        async def enhanced_patient_search(name=None, identifier=None, **params):
            # Construct search parameters
            search_params = {}
            if name:
                search_params["name"] = name
            if identifier:
                search_params["identifier"] = identifier

            # Get search results from FHIR server
            return fhir_client.client.server.request_json("Patient", params=search_params)

        # Use the client
        result = await fhir_client.handle("patient_search", name="Smith")
        ```
    """

    def __init__(self, base_url=None, client=None, **options):
        """
        Initialize a new FHIR client.

        Args:
            base_url: The base URL of the FHIR server
            client: An existing FHIR client instance to use, or None to create a new one
            **options: Additional configuration options
        """
        super().__init__(**options)

        # Create default FHIR client if not provided
        if client is None and base_url:
            if fhir_client is None:
                raise ImportError(
                    "fhirclient package is required. Install with 'pip install fhirclient'"
                )
            client = fhir_client.FHIRClient(
                settings={
                    "app_id": options.get("app_id", "healthchain"),
                    "api_base": base_url,
                }
            )

        self.client = client
        self.base_url = base_url

    def operation(self, operation_name: str):
        """
        Decorator to register a handler for a specific FHIR operation.

        Args:
            operation_name: The operation name to handle

        Returns:
            Decorator function that registers the handler
        """

        def decorator(handler):
            self.register_handler(operation_name, handler)
            return handler

        return decorator

    async def _default_handler(self, operation: str, **params) -> Any:
        """
        Default handler for operations without registered handlers.

        Implements common FHIR operations like search and read.

        Args:
            operation: The operation name (e.g., "search", "read")
            **params: Operation parameters

        Returns:
            Result of the FHIR operation
        """
        resource_type = params.get("resource_type")

        if not resource_type:
            raise ValueError(f"Resource type is required for operation: {operation}")

        if operation == "search" and resource_type:
            search_params = params.get("params", {})
            if self.client:
                return self.client.server.request_json(
                    resource_type, params=search_params
                )
            else:
                # Fallback to direct HTTP if no client
                url = f"{self.base_url}/{resource_type}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=search_params) as response:
                        return await response.json()

        elif operation == "read" and resource_type:
            resource_id = params.get("id")
            if not resource_id:
                raise ValueError("Resource ID is required for read operation")

            if self.client:
                return self.client.server.request_json(f"{resource_type}/{resource_id}")
            else:
                # Fallback to direct HTTP if no client
                url = f"{self.base_url}/{resource_type}/{resource_id}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        return await response.json()

        elif operation == "create" and resource_type:
            resource_data = params.get("resource")
            if not resource_data:
                raise ValueError("Resource data is required for create operation")

            if self.client:
                return self.client.server.post_json(resource_type, resource_data)
            else:
                # Fallback to direct HTTP if no client
                url = f"{self.base_url}/{resource_type}"
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=resource_data) as response:
                        return await response.json()

        raise ValueError(f"Unsupported operation: {operation}")

    def get_capabilities(self) -> List[str]:
        """
        Get list of supported FHIR operations.

        Returns:
            List of operations this client supports
        """
        # Built-in operations plus custom handlers
        built_in = ["search", "read", "create"]
        return built_in + [op for op in self._handlers.keys() if op not in built_in]
