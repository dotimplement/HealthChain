"""
FHIR client interfaces and implementations.

This module provides standardized interfaces for different FHIR client libraries.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from fhir.resources.resource import Resource

logger = logging.getLogger(__name__)


def _get_fhirclient_resource_class(resource_type: str):
    """Get the FHIR resource class from fhirclient.models.

    Args:
        resource_type: The FHIR resource type (e.g. 'Patient', 'Observation')

    Returns:
        The resource class from fhirclient.models

    Raises:
        ImportError: If the resource class cannot be imported
    """
    module_name = f"fhirclient.models.{resource_type.lower()}"
    try:
        module = __import__(module_name, fromlist=[resource_type])
        return getattr(module, resource_type)
    except (ImportError, AttributeError) as e:
        raise ImportError(
            f"Failed to import FHIR client resource {resource_type}: {str(e)}"
        )


def create_fhir_server(
    base_url: str,
    auth: str = None,
    client_id: str = None,
    client_secret: str = None,
    redirect_uri: str = None,
    patient_id: str = None,
    scope: str = None,
    launch_token: str = None,
    timeout: int = 30,
    **additional_params,
) -> "FHIRServerInterface":
    """
    Factory function to create and configure a FHIR server interface.

    Args:
        base_url: The FHIR server base URL
        auth: Authentication type ('oauth', 'basic', etc.)
        client_id: OAuth client ID or username for basic auth
        client_secret: OAuth client secret or password for basic auth
        redirect_uri: OAuth redirect URI
        patient_id: Optional patient context
        scope: OAuth scopes (space-separated)
        launch_token: Launch token for EHR launch
        timeout: Request timeout in seconds
        **additional_params: Additional parameters for the client

    Returns:
        A configured FHIRServerInterface implementation
    """
    # Prepare the settings dictionary for fhirclient
    settings = {"api_base": base_url, "timeout": timeout}

    # Add auth-related settings based on auth type
    if auth == "oauth":
        settings.update(
            {
                "app_id": client_id,
                "app_secret": client_secret,
                "redirect_uri": redirect_uri,
            }
        )

        # Add optional OAuth parameters if provided
        if scope:
            settings["scope"] = scope
        if launch_token:
            settings["launch_token"] = launch_token

    elif auth == "basic":
        # For basic auth, we'll use app_id as username and app_secret as password
        settings.update(
            {"app_id": client_id, "app_secret": client_secret, "auth_type": "basic"}
        )

    # Add patient context if provided
    if patient_id:
        settings["patient_id"] = patient_id

    # Add any additional parameters
    settings.update(additional_params)

    logger.debug(f"Creating FHIR server for {base_url} with auth type: {auth}")

    # Create and return the server instance
    return FHIRServer(settings)


class FHIRServerInterface(ABC):
    """
    Interface for FHIR servers.

    Provides a standardized interface for interacting with FHIR servers
    using different client libraries.
    """

    @abstractmethod
    async def read(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        """Get a resource or search results."""
        pass

    @abstractmethod
    async def create(self, resource_type: str, resource: Dict) -> Dict:
        """Create a new resource."""
        pass

    @abstractmethod
    async def update(self, resource_type: str, id: str, resource: Dict) -> Dict:
        """Update an existing resource."""
        pass

    @abstractmethod
    async def delete(self, resource_type: str, id: str) -> Dict:
        """Delete a resource."""
        pass

    @abstractmethod
    async def search(
        self, resource_type: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """Search for resources."""
        pass

    @abstractmethod
    async def transaction(self, bundle: Dict) -> Dict:
        """Execute a transaction bundle."""
        pass

    @abstractmethod
    async def capabilities(self) -> Dict:
        """Get the capabilities of the FHIR server."""
        pass


class FHIRServer(FHIRServerInterface):
    """
    Adapter for the fhirclient library.

    This class wraps the SMART on FHIR client-py library to provide a standardized interface
    for interacting with FHIR servers. It handles the conversion between fhirclient.models
    objects and our fhir.resource models.

    It's a bit roundabout as we need to convert the resource object to a fhirclient.models
    object and back again. But I'd rather use an actively maintained library than roll our own atm.
    """

    def __init__(self, settings: Dict[str, Any]):
        """
        Initialize the FHIR server adapter with client settings.

        Args:
            settings (Dict[str, Any]): Configuration settings for the FHIR client
        """
        try:
            import fhirclient.client as smart_client
        except ImportError:
            raise ImportError("fhirclient library is required for FHIR server adapter")

        self.client = smart_client.FHIRClient(settings=settings)

    def read(self, resource: Resource, resource_id: str) -> Optional[Resource]:
        """Get a resource by ID.

        Args:
            resource (Resource): The resource type to read
            resource_id (str): The ID of the resource to retrieve

        Returns:
            Optional[Resource]: The retrieved resource or None if an error occurs
        """
        # We need to convert the resource object to fhirclient.models
        resource_class = _get_fhirclient_resource_class(resource.__resource_type__)

        result = resource_class.read(resource_id, self.client)

        # Convert the result back to a pydantic model
        try:
            return resource(**result.as_json())
        except Exception as e:
            logger.error(f"Resource response validation error: {e}")

            # TODO: use FHIR error handling
            return None

    def create(self, resource: Resource) -> Optional[Resource]:
        """Create a new resource.

        Args:
            resource (Resource): The resource to create

        Returns:
            Optional[Resource]: The created resource or None if an error occurs
        """
        # We need to convert the resource object to fhirclient.models
        resource_class = _get_fhirclient_resource_class(resource.__resource_type__)

        result = resource_class.create(self.client)

        # Convert the result back to a pydantic model
        try:
            return resource(**result.as_json())
        except Exception as e:
            logger.error(f"Resource response validation error: {e}")
            return None

    def update(self, resource: Resource) -> Optional[Resource]:
        """Update an existing resource.

        Args:
            resource (Resource): The resource to update

        Returns:
            Optional[Resource]: The updated resource or None if an error occurs
        """
        # We need to convert the resource object to fhirclient.models
        resource_class = _get_fhirclient_resource_class(resource.__resource_type__)

        result = resource_class.update(self.client)

        # Convert the result back to a pydantic model
        try:
            return resource(**result.as_json())
        except Exception as e:
            logger.error(f"Resource response validation error: {e}")
            return None

    def delete(self, resource: Resource) -> Optional[Resource]:
        """Delete a resource.

        Args:
            resource (Resource): The resource to delete

        Returns:
            Optional[Resource]: The deleted resource or None if an error occurs
        """
        # We need to convert the resource object to fhirclient.models
        resource_class = _get_fhirclient_resource_class(resource.__resource_type__)

        result = resource_class.delete(self.client)

        # Convert the result back to a pydantic model
        try:
            return resource(**result.as_json())
        except Exception as e:
            logger.error(f"Resource response validation error: {e}")
            return None

    def search(
        self, resource: Resource, params: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Resource]]:
        """Search for resources.

        Args:
            resource (Resource): The resource type to search for
            params (Optional[Dict[str, Any]]): Search parameters

        Returns:
            Optional[List[Resource]]: List of matching resources or None if an error occurs
        """
        # We need to convert the resource object to fhirclient.models
        resource_class = _get_fhirclient_resource_class(resource.__resource_type__)

        result = resource_class.search(self.client, params)

        # Convert the result back to a pydantic model
        try:
            return [resource(**r.as_json()) for r in result]
        except Exception as e:
            logger.error(f"Resource response validation error: {e}")
            return None

    def transaction(self, bundle: List[Resource]) -> Optional[List[Resource]]:
        """Execute a transaction bundle.

        Args:
            bundle (List[Resource]): List of resources to process in the transaction

        Returns:
            Optional[List[Resource]]: List of processed resources or None if an error occurs
        """
        pass

    def capabilities(self) -> Dict:
        """Get the capabilities of the FHIR server.

        Returns:
            Dict: Server capabilities information
        """
        return self.client.prepare()
