"""
FHIR client interfaces and implementations.

This module provides standardized interfaces for different FHIR client libraries.
"""

import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, Type
from urllib.parse import urljoin, urlencode
import httpx
from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle
from fhir.resources.capabilitystatement import CapabilityStatement

logger = logging.getLogger(__name__)


class FHIRClientError(Exception):
    """Base exception for FHIR client errors."""

    def __init__(
        self, message: str, status_code: int = None, response_data: dict = None
    ):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


def create_fhir_server(
    base_url: str,
    access_token: str = None,
    auth: str = None,
    timeout: int = 30,
    **additional_params,
) -> "FHIRServerInterface":
    """
    Factory function to create and configure a FHIR server interface.

    Args:
        base_url: The FHIR server base URL
        access_token: JWT access token for Bearer authentication
        auth: Authentication type (deprecated, use access_token)
        timeout: Request timeout in seconds
        **additional_params: Additional parameters for the client

    Returns:
        A configured FHIRServerInterface implementation
    """
    logger.debug(f"Creating FHIR server for {base_url}")

    return AsyncFHIRClient(
        base_url=base_url,
        access_token=access_token,
        timeout=timeout,
        **additional_params,
    )


class FHIRServerInterface(ABC):
    """
    Interface for FHIR servers.

    Provides a standardized interface for interacting with FHIR servers
    using different client libraries.
    """

    @abstractmethod
    async def read(
        self, resource_type: Union[str, Type[Resource]], resource_id: str
    ) -> Resource:
        """Read a specific resource by ID."""
        pass

    @abstractmethod
    async def create(self, resource: Resource) -> Resource:
        """Create a new resource."""
        pass

    @abstractmethod
    async def update(self, resource: Resource) -> Resource:
        """Update an existing resource."""
        pass

    @abstractmethod
    async def delete(
        self, resource_type: Union[str, Type[Resource]], resource_id: str
    ) -> bool:
        """Delete a resource."""
        pass

    @abstractmethod
    async def search(
        self,
        resource_type: Union[str, Type[Resource]],
        params: Optional[Dict[str, Any]] = None,
    ) -> Bundle:
        """Search for resources."""
        pass

    @abstractmethod
    async def transaction(self, bundle: Bundle) -> Bundle:
        """Execute a transaction bundle."""
        pass

    @abstractmethod
    async def capabilities(self) -> CapabilityStatement:
        """Get the capabilities of the FHIR server."""
        pass


class AsyncFHIRClient(FHIRServerInterface):
    """
    Async FHIR client optimized for HealthChain gateway use cases.

    - Uses fhir.resources for validation
    - Supports JWT Bearer token authentication
    - Async-first with httpx
    """

    def __init__(
        self,
        base_url: str,
        access_token: str = None,
        timeout: int = 30,
        verify_ssl: bool = True,
        **kwargs,
    ):
        """
        Initialize the FHIR client.

        Args:
            base_url: FHIR server base URL (e.g., "https://fhir.epic.com/api/FHIR/R4/")
            access_token: JWT access token for authentication
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            **kwargs: Additional parameters
        """
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

        # Setup headers
        self.headers = {
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        }

        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"

        # Create httpx client
        self.client = httpx.AsyncClient(
            timeout=timeout, verify=verify_ssl, headers=self.headers
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _build_url(self, path: str, params: Dict[str, Any] = None) -> str:
        """Build a complete URL with optional query parameters."""
        url = urljoin(self.base_url, path)
        if params:
            # Filter out None values and convert to strings
            clean_params = {k: str(v) for k, v in params.items() if v is not None}
            if clean_params:
                url += "?" + urlencode(clean_params)
        return url

    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle HTTP response and convert to dict."""
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise FHIRClientError(
                f"Invalid JSON response: {response.text}",
                status_code=response.status_code,
            )

        if not response.is_success:
            error_msg = f"FHIR request failed: {response.status_code}"
            if isinstance(data, dict) and "issue" in data:
                # FHIR OperationOutcome format
                issues = data.get("issue", [])
                if issues:
                    error_msg += f" - {issues[0].get('diagnostics', 'Unknown error')}"

            raise FHIRClientError(
                error_msg, status_code=response.status_code, response_data=data
            )

        return data

    async def capabilities(self) -> CapabilityStatement:
        """
        Fetch the server's CapabilityStatement.

        Returns:
            CapabilityStatement resource
        """
        response = await self.client.get(self._build_url("metadata"))
        data = self._handle_response(response)
        return CapabilityStatement(**data)

    async def read(
        self, resource_type: Union[str, Type[Resource]], resource_id: str
    ) -> Resource:
        """
        Read a specific resource by ID.

        Args:
            resource_type: FHIR resource type or class
            resource_id: Resource ID

        Returns:
            Resource instance
        """
        if hasattr(resource_type, "__name__"):
            type_name = resource_type.__name__
            resource_class = resource_type
        else:
            type_name = str(resource_type)
            # Dynamically import the resource class
            module_name = f"fhir.resources.{type_name.lower()}"
            module = __import__(module_name, fromlist=[type_name])
            resource_class = getattr(module, type_name)

        url = self._build_url(f"{type_name}/{resource_id}")
        response = await self.client.get(url)
        data = self._handle_response(response)

        return resource_class(**data)

    async def search(
        self, resource_type: Union[str, Type[Resource]], params: Dict[str, Any] = None
    ) -> Bundle:
        """
        Search for resources.

        Args:
            resource_type: FHIR resource type or class
            params: Search parameters

        Returns:
            Bundle containing search results
        """
        if hasattr(resource_type, "__name__"):
            type_name = resource_type.__name__
        else:
            type_name = str(resource_type)

        url = self._build_url(type_name, params)
        response = await self.client.get(url)
        data = self._handle_response(response)

        return Bundle(**data)

    async def create(self, resource: Resource) -> Resource:
        """
        Create a new resource.

        Args:
            resource: Resource to create

        Returns:
            Created resource with server-assigned ID
        """
        resource_type = resource.__resource_type__
        url = self._build_url(resource_type)

        response = await self.client.post(url, content=resource.model_dump_json())
        data = self._handle_response(response)

        # Return the same resource type
        resource_class = type(resource)
        return resource_class(**data)

    async def update(self, resource: Resource) -> Resource:
        """
        Update an existing resource.

        Args:
            resource: Resource to update (must have ID)

        Returns:
            Updated resource
        """
        if not resource.id:
            raise ValueError("Resource must have an ID for update")

        resource_type = resource.__resource_type__
        url = self._build_url(f"{resource_type}/{resource.id}")

        response = await self.client.put(url, content=resource.model_dump_json())
        data = self._handle_response(response)

        # Return the same resource type
        resource_class = type(resource)
        return resource_class(**data)

    async def delete(
        self, resource_type: Union[str, Type[Resource]], resource_id: str
    ) -> bool:
        """
        Delete a resource.

        Args:
            resource_type: FHIR resource type or class
            resource_id: Resource ID to delete

        Returns:
            True if successful
        """
        if hasattr(resource_type, "__name__"):
            type_name = resource_type.__name__
        else:
            type_name = str(resource_type)

        url = self._build_url(f"{type_name}/{resource_id}")
        response = await self.client.delete(url)

        # Delete operations typically return 204 No Content
        if response.status_code in (200, 204):
            return True

        self._handle_response(response)  # This will raise an error
        return False

    async def transaction(self, bundle: Bundle) -> Bundle:
        """
        Execute a transaction bundle.

        Args:
            bundle: Transaction bundle

        Returns:
            Response bundle
        """
        url = self._build_url("")  # Base URL for transaction

        response = await self.client.post(url, content=bundle.model_dump_json())
        data = self._handle_response(response)

        return Bundle(**data)
