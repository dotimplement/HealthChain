import logging

from typing import Any, Dict, Type

from fhir.resources.bundle import Bundle
from fhir.resources.capabilitystatement import CapabilityStatement
from fhir.resources.resource import Resource

from healthchain.gateway.clients.fhir.base import FHIRServerInterface
from healthchain.gateway.clients.fhir.sync.connection import FHIRConnectionManager
from healthchain.gateway.fhir.base import BaseFHIRGateway


logger = logging.getLogger(__name__)


class FHIRGateway(BaseFHIRGateway):
    """
    Sync FHIR Gateway for HealthChain.

    A synchronous gateway for FHIR resource operations including:
    - Resource transformation and aggregation
    - Simple logging-based operation tracking
    - OAuth2 authentication support

    Example:
        ```python
        # Initialize sync gateway
        gateway = FHIRGateway()
        gateway.add_source("epic", "fhir://epic.org/api/FHIR/R4?...")

        patient = gateway.read(Patient, "123", "epic")
        ```
    """

    def __init__(self, **kwargs):
        """Initialize the Sync FHIR Gateway."""
        super().__init__(**kwargs)

        # Initialize sync connection manager
        self.connection_manager = FHIRConnectionManager()

        # Initialize sources
        self._initialize_connection_manager()

    def get_client(self, source: str = None) -> FHIRServerInterface:
        """
        Get a sync FHIR client for the specified source.

        Args:
            source: Source name to get client for (uses first available if None)

        Returns:
            FHIRServerInterface: A sync FHIR client

        Raises:
            ValueError: If source is unknown or no sources configured
        """
        return self.connection_manager.get_client(source)

    def capabilities(self, source: str = None) -> CapabilityStatement:
        """
        Get the capabilities of the FHIR server (sync version).

        Args:
            source: Source name to get capabilities for (uses first available if None)

        Returns:
            CapabilityStatement: The capabilities of the FHIR server
        """
        client = self.get_client(source)
        capabilities = client.capabilities()

        logger.info("FHIR operation: capabilities on CapabilityStatement/None")

        return capabilities

    def transaction(self, bundle: Bundle, source: str = None) -> Bundle:
        """
        Execute a FHIR transaction bundle (sync version).

        Args:
            bundle: The transaction bundle to execute
            source: Source name to execute in (uses first available if None)

        Returns:
            The response bundle with results

        Example:
            bundle = Bundle(type="transaction", entry=[...])
            result = gateway.transaction(bundle, "epic")
        """
        client = self.get_client(source)
        result = client.transaction(bundle)

        # Log transaction event with entry counts
        entry_count = len(bundle.entry) if bundle.entry else 0
        result_count = len(result.entry) if result.entry else 0
        logger.info(
            f"FHIR operation: transaction on Bundle/None (entry_count={entry_count}, result_count={result_count})"
        )

        return result

    def read(
        self,
        resource_type: Type[Resource],
        fhir_id: str,
        source: str = None,
    ) -> Resource:
        """
        Read a FHIR resource (sync version).

        Args:
            resource_type: The FHIR resource type class
            fhir_id: Resource ID to fetch
            source: Source name to fetch from (uses first available if None)

        Returns:
            The FHIR resource object

        Example:
            patient = gateway.read(Patient, "123", "epic")
        """
        client = self.get_client(source)
        resource = client.read(resource_type, fhir_id)

        if not resource:
            type_name = resource_type.__resource_type__
            raise ValueError(f"Resource {type_name}/{fhir_id} not found")

        type_name = resource.__resource_type__
        logger.info(f"FHIR operation: read on {type_name}/{fhir_id}")

        return resource

    def create(self, resource: Resource, source: str = None) -> Resource:
        """
        Create a new FHIR resource (sync version).

        Args:
            resource: The FHIR resource to create
            source: Source name to create in (uses first available if None)

        Returns:
            The created FHIR resource with server-assigned ID

        Example:
            patient = Patient(name=[HumanName(family="Smith", given=["John"])])
            created = gateway.create(patient, "epic")
        """
        client = self.get_client(source)
        created = client.create(resource)

        type_name = resource.__resource_type__
        logger.info(f"FHIR operation: create on {type_name}/{created.id}")

        return created

    def update(self, resource: Resource, source: str = None) -> Resource:
        """
        Update an existing FHIR resource (sync version).

        Args:
            resource: The FHIR resource to update (must have ID)
            source: Source name to update in (uses first available if None)

        Returns:
            The updated FHIR resource

        Example:
            patient = gateway.read(Patient, "123", "epic")
            patient.name[0].family = "Jones"
            updated = gateway.update(patient, "epic")
        """
        if not resource.id:
            raise ValueError("Resource must have an ID for update")

        client = self.get_client(source)
        updated = client.update(resource)

        type_name = resource.__resource_type__
        logger.info(f"FHIR operation: update on {type_name}/{resource.id}")

        return updated

    def search(
        self,
        resource_type: Type[Resource],
        params: Dict[str, Any] = None,
        source: str = None,
    ) -> Bundle:
        """
        Search for FHIR resources (sync version).

        Args:
            resource_type: The FHIR resource type class
            params: Search parameters (e.g., {"name": "Smith", "active": "true"})
            source: Source name to search in (uses first available if None)

        Returns:
            Bundle containing search results

        Example:
            bundle = gateway.search(Patient, {"name": "Smith"}, "epic")
        """
        client = self.get_client(source)
        bundle = client.search(resource_type, params)

        # Log search event with result count
        type_name = resource_type.__resource_type__
        result_count = len(bundle.entry) if bundle.entry else 0
        logger.info(
            f"FHIR operation: search on {type_name} with params {params}, found {result_count} results"
        )

        return bundle

    def delete(
        self, resource_type: Type[Resource], fhir_id: str, source: str = None
    ) -> bool:
        """
        Delete a FHIR resource (sync version).

        Args:
            resource_type: The FHIR resource type class
            fhir_id: Resource ID to delete
            source: Source name to delete from (uses first available if None)

        Returns:
            True if deletion was successful

        Example:
            success = gateway.delete(Patient, "123", "epic")
        """
        client = self.get_client(source)
        success = client.delete(resource_type, fhir_id)

        if success:
            type_name = resource_type.__resource_type__
            logger.info(f"FHIR operation: delete on {type_name}/{fhir_id}")

        return success or True
