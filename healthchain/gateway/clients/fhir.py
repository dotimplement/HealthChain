"""
FHIR client interfaces and implementations.

This module provides standardized interfaces for different FHIR client libraries.
"""

import logging
import json
import httpx

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, Type
from urllib.parse import urljoin, urlencode
from functools import lru_cache

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle
from fhir.resources.capabilitystatement import CapabilityStatement

from healthchain.gateway.clients.auth import (
    OAuth2TokenManager,
    SyncOAuth2TokenManager,
    FHIRAuthConfig,
)


logger = logging.getLogger(__name__)


def create_fhir_client(
    auth_config: FHIRAuthConfig,
    limits: httpx.Limits = None,
    async_client: bool = True,
    **additional_params,
) -> "FHIRServerInterface":
    """
    Factory function to create and configure a FHIR server interface using OAuth2.0

    Args:
        auth_config: OAuth2.0 authentication configuration
        limits: httpx connection limits for pooling
        async_client: If True, returns AsyncFHIRClient; if False, returns SyncFHIRClient
        **additional_params: Additional parameters for the client

    Returns:
        A configured FHIRServerInterface or SyncFHIRServerInterface implementation
    """
    logger.debug(
        f"Creating {'async' if async_client else 'sync'} FHIR server with OAuth2.0 for {auth_config.base_url}"
    )

    if async_client:
        return AsyncFHIRClient(
            auth_config=auth_config, limits=limits, **additional_params
        )
    else:
        return SyncFHIRClient(
            auth_config=auth_config, limits=limits, **additional_params
        )


class FHIRClientError(Exception):
    """Base exception for FHIR client errors."""

    def __init__(
        self, message: str, status_code: int = None, response_data: dict = None
    ):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class FHIRServerInterface(ABC):
    """
    Base FHIR client interface with common functionality.

    Provides a standardized interface for interacting with FHIR servers
    using different client libraries, with shared utility methods.
    """

    def __init__(self, auth_config: FHIRAuthConfig):
        """Initialize common client properties."""
        self.base_url = auth_config.base_url.rstrip("/") + "/"
        self.timeout = auth_config.timeout
        self.verify_ssl = auth_config.verify_ssl

        # Setup base headers
        self.base_headers = {
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        }

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

    @lru_cache(maxsize=128)
    def _resolve_resource_type(
        self, resource_type: Union[str, Type[Resource]]
    ) -> tuple[str, Type[Resource]]:
        """
        Resolve FHIR resource type to string name and class. Cached with LRU.

        Args:
            resource_type: FHIR resource type or class

        Returns:
            Tuple of (type_name: str, resource_class: Type[Resource])
        """
        if hasattr(resource_type, "__name__"):
            # It's already a class
            type_name = resource_type.__name__
            resource_class = resource_type
        else:
            # It's a string, need to dynamically import
            type_name = str(resource_type)
            module_name = f"fhir.resources.{type_name.lower()}"
            module = __import__(module_name, fromlist=[type_name])
            resource_class = getattr(module, type_name)

        return type_name, resource_class

    @abstractmethod
    def read(
        self, resource_type: Union[str, Type[Resource]], resource_id: str
    ) -> Resource:
        """Read a specific resource by ID."""
        pass

    @abstractmethod
    def create(self, resource: Resource) -> Resource:
        """Create a new resource."""
        pass

    @abstractmethod
    def update(self, resource: Resource) -> Resource:
        """Update an existing resource."""
        pass

    @abstractmethod
    def delete(
        self, resource_type: Union[str, Type[Resource]], resource_id: str
    ) -> bool:
        """Delete a resource."""
        pass

    @abstractmethod
    def search(
        self,
        resource_type: Union[str, Type[Resource]],
        params: Optional[Dict[str, Any]] = None,
    ) -> Bundle:
        """Search for resources."""
        pass

    @abstractmethod
    def transaction(self, bundle: Bundle) -> Bundle:
        """Execute a transaction bundle."""
        pass

    @abstractmethod
    def capabilities(self) -> CapabilityStatement:
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
        auth_config: FHIRAuthConfig,
        limits: httpx.Limits = None,
        **kwargs,
    ):
        """
        Initialize the FHIR client with OAuth2.0 authentication.

        Args:
            auth_config: OAuth2.0 authentication configuration
            limits: httpx connection limits for pooling
            **kwargs: Additional parameters passed to httpx.AsyncClient
        """
        super().__init__(auth_config)
        self.token_manager = OAuth2TokenManager(auth_config.to_oauth2_config())

        # Create httpx client with connection pooling and additional kwargs
        client_kwargs = {"timeout": self.timeout, "verify": self.verify_ssl}
        if limits is not None:
            client_kwargs["limits"] = limits

        # Pass through additional kwargs to httpx.AsyncClient
        client_kwargs.update(kwargs)

        self.client = httpx.AsyncClient(**client_kwargs)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with fresh OAuth2.0 token."""
        headers = self.base_headers.copy()
        token = await self.token_manager.get_access_token()
        headers["Authorization"] = f"Bearer {token}"
        return headers

    async def capabilities(self) -> CapabilityStatement:
        """
        Fetch the server's CapabilityStatement.

        Returns:
            CapabilityStatement resource
        """
        headers = await self._get_headers()
        response = await self.client.get(self._build_url("metadata"), headers=headers)
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
        type_name, resource_class = self._resolve_resource_type(resource_type)
        url = self._build_url(f"{type_name}/{resource_id}")
        logger.debug(f"Sending GET request to {url}")

        headers = await self._get_headers()
        response = await self.client.get(url, headers=headers)
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
        type_name, _ = self._resolve_resource_type(resource_type)
        url = self._build_url(type_name, params)
        logger.debug(f"Sending GET request to {url}")

        headers = await self._get_headers()
        response = await self.client.get(url, headers=headers)
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
        type_name, resource_class = self._resolve_resource_type(
            resource.__resource_type__
        )
        url = self._build_url(type_name)
        logger.debug(f"Sending POST request to {url}")

        headers = await self._get_headers()
        response = await self.client.post(
            url, content=resource.model_dump_json(), headers=headers
        )
        data = self._handle_response(response)

        # Return the same resource type
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

        type_name, resource_class = self._resolve_resource_type(
            resource.__resource_type__
        )
        url = self._build_url(f"{type_name}/{resource.id}")
        logger.debug(f"Sending PUT request to {url}")

        headers = await self._get_headers()
        response = await self.client.put(
            url, content=resource.model_dump_json(), headers=headers
        )
        data = self._handle_response(response)

        # Return the same resource type
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
        type_name, _ = self._resolve_resource_type(resource_type)
        url = self._build_url(f"{type_name}/{resource_id}")
        logger.debug(f"Sending DELETE request to {url}")

        headers = await self._get_headers()
        response = await self.client.delete(url, headers=headers)

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
        logger.debug(f"Sending POST request to {url}")

        headers = await self._get_headers()
        response = await self.client.post(
            url, content=bundle.model_dump_json(), headers=headers
        )
        data = self._handle_response(response)

        return Bundle(**data)


class SyncFHIRClient(FHIRServerInterface):
    """
    Synchronous FHIR client optimized for HealthChain gateway use cases.

    - Uses fhir.resources for validation
    - Supports JWT Bearer token authentication
    - Synchronous with httpx
    """

    def __init__(
        self,
        auth_config: FHIRAuthConfig,
        limits: httpx.Limits = None,
        **kwargs,
    ):
        """
        Initialize the FHIR client with OAuth2.0 authentication.

        Args:
            auth_config: OAuth2.0 authentication configuration
            limits: httpx connection limits for pooling
            **kwargs: Additional parameters passed to httpx.Client
        """
        super().__init__(auth_config)
        self.token_manager = SyncOAuth2TokenManager(auth_config.to_oauth2_config())

        # Create httpx client with connection pooling and additional kwargs
        client_kwargs = {"timeout": self.timeout, "verify": self.verify_ssl}
        if limits is not None:
            client_kwargs["limits"] = limits

        # Pass through additional kwargs to httpx.Client
        client_kwargs.update(kwargs)

        self.client = httpx.Client(**client_kwargs)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with fresh OAuth2.0 token."""
        headers = self.base_headers.copy()
        token = self.token_manager.get_access_token()
        headers["Authorization"] = f"Bearer {token}"
        return headers

    def capabilities(self) -> CapabilityStatement:
        """
        Fetch the server's CapabilityStatement.

        Returns:
            CapabilityStatement resource
        """
        headers = self._get_headers()
        response = self.client.get(self._build_url("metadata"), headers=headers)
        data = self._handle_response(response)
        return CapabilityStatement(**data)

    def read(
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
        type_name, resource_class = self._resolve_resource_type(resource_type)
        url = self._build_url(f"{type_name}/{resource_id}")
        logger.debug(f"Sending GET request to {url}")

        headers = self._get_headers()
        response = self.client.get(url, headers=headers)
        data = self._handle_response(response)

        return resource_class(**data)

    def search(
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
        type_name, _ = self._resolve_resource_type(resource_type)
        url = self._build_url(type_name, params)
        logger.debug(f"Sending GET request to {url}")

        headers = self._get_headers()
        response = self.client.get(url, headers=headers)
        data = self._handle_response(response)

        return Bundle(**data)

    def create(self, resource: Resource) -> Resource:
        """
        Create a new resource.

        Args:
            resource: Resource to create

        Returns:
            Created resource with server-assigned ID
        """
        type_name, resource_class = self._resolve_resource_type(
            resource.__resource_type__
        )
        url = self._build_url(type_name)
        logger.debug(f"Sending POST request to {url}")

        headers = self._get_headers()
        response = self.client.post(
            url, content=resource.model_dump_json(), headers=headers
        )
        data = self._handle_response(response)

        # Return the same resource type
        return resource_class(**data)

    def update(self, resource: Resource) -> Resource:
        """
        Update an existing resource.

        Args:
            resource: Resource to update (must have ID)

        Returns:
            Updated resource
        """
        if not resource.id:
            raise ValueError("Resource must have an ID for update")

        type_name, resource_class = self._resolve_resource_type(
            resource.__resource_type__
        )
        url = self._build_url(f"{type_name}/{resource.id}")
        logger.debug(f"Sending PUT request to {url}")

        headers = self._get_headers()
        response = self.client.put(
            url, content=resource.model_dump_json(), headers=headers
        )
        data = self._handle_response(response)

        # Return the same resource type
        return resource_class(**data)

    def delete(
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
        type_name, _ = self._resolve_resource_type(resource_type)
        url = self._build_url(f"{type_name}/{resource_id}")
        logger.debug(f"Sending DELETE request to {url}")

        headers = self._get_headers()
        response = self.client.delete(url, headers=headers)

        # Delete operations typically return 204 No Content
        if response.status_code in (200, 204):
            return True

        self._handle_response(response)  # This will raise an error
        return False

    def transaction(self, bundle: Bundle) -> Bundle:
        """
        Execute a transaction bundle.

        Args:
            bundle: Transaction bundle

        Returns:
            Response bundle
        """
        url = self._build_url("")  # Base URL for transaction
        logger.debug(f"Sending POST request to {url}")

        headers = self._get_headers()
        response = self.client.post(
            url, content=bundle.model_dump_json(), headers=headers
        )
        data = self._handle_response(response)

        return Bundle(**data)
