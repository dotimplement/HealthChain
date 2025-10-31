import logging

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Type

from fhir.resources.bundle import Bundle
from fhir.resources.capabilitystatement import CapabilityStatement
from fhir.resources.resource import Resource

from healthchain.gateway.clients.fhir.base import FHIRServerInterface
from healthchain.gateway.clients.fhir.aio.connection import AsyncFHIRConnectionManager
from healthchain.gateway.fhir.errors import FHIRErrorHandler
from healthchain.gateway.fhir.base import BaseFHIRGateway
from healthchain.gateway.events.fhir import create_fhir_event
from healthchain.fhir import add_provenance_metadata


logger = logging.getLogger(__name__)


class AsyncFHIRGateway(BaseFHIRGateway):
    """
    Async FHIR Gateway for HealthChain.

    A specialized async gateway for FHIR resource operations including:
    - Connection pooling and management
    - Resource transformation and aggregation
    - Event-driven processing
    - OAuth2 authentication support

    Example:
        ```python
        # Initialize with connection pooling
        async with AsyncFHIRGateway(max_connections=50) as gateway:
            # Add FHIR source
            gateway.add_source("epic", "fhir://epic.org/api/FHIR/R4?...")

            # Use the gateway
            patient = await gateway.read(Patient, "123", "epic")
        ```
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 5.0,
        **kwargs,
    ):
        """Initialize the Async FHIR Gateway."""
        super().__init__(**kwargs)

        # Initialize async connection manager with pooling
        self.connection_manager = AsyncFHIRConnectionManager(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        )

        # Initialize sources
        self._initialize_connection_manager()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close all connections and clean up resources."""
        await self.connection_manager.close()

    async def get_client(self, source: str = None) -> FHIRServerInterface:
        """
        Get a FHIR client for the specified source.

        Args:
            source: Source name to get client for (uses first available if None)

        Returns:
            FHIRServerInterface: A FHIR client with pooled connections
        """
        return await self.connection_manager.get_client(source)

    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get the current status of the connection pool.

        Returns:
            Dict containing pool status information including:
            - max_connections: Maximum connections across all sources
            - sources: Dict of source names and their connection info
            - client_stats: Detailed httpx connection pool statistics
        """
        return self.connection_manager.get_status()

    async def capabilities(self, source: str = None) -> CapabilityStatement:
        """
        Get the capabilities of the FHIR server.

        Args:
            source: Source name to get capabilities for (uses first available if None)

        Returns:
            CapabilityStatement: The capabilities of the FHIR server

        Raises:
            FHIRConnectionError: If connection fails
        """
        capabilities = await self._execute_with_client(
            "capabilities",
            source=source,
            resource_type=CapabilityStatement,
        )

        # Emit capabilities event
        self._emit_fhir_event("capabilities", "CapabilityStatement", None, capabilities)
        logger.debug("Retrieved server capabilities")

        return capabilities

    async def read(
        self,
        resource_type: Type[Resource],
        fhir_id: str,
        source: str = None,
    ) -> Resource:
        """
        Read a FHIR resource.

        Args:
            resource_type: The FHIR resource type class
            fhir_id: Resource ID to fetch
            source: Source name to fetch from (uses first available if None)

        Returns:
            The FHIR resource object

        Raises:
            ValueError: If resource not found or source invalid
            FHIRConnectionError: If connection fails

        Example:
            # Simple read-only access
            document = await fhir_gateway.read(DocumentReference, "123", "epic")
            summary = extract_summary(document.text)
        """
        resource = await self._execute_with_client(
            "read",
            source=source,
            resource_type=resource_type,
            resource_id=fhir_id,
            client_args=(resource_type, fhir_id),
        )

        if not resource:
            type_name = resource_type.__resource_type__
            raise ValueError(f"Resource {type_name}/{fhir_id} not found")

        # Emit read event
        type_name = resource.__resource_type__
        self._emit_fhir_event("read", type_name, fhir_id, resource)
        logger.debug(f"Retrieved {type_name}/{fhir_id} for read-only access")

        return resource

    async def search(
        self,
        resource_type: Type[Resource],
        params: Dict[str, Any] = None,
        source: str = None,
        add_provenance: bool = False,
        provenance_tag: str = None,
        follow_pagination: bool = False,
        max_pages: Optional[int] = None,
    ) -> Bundle:
        """
        Search for FHIR resources.

        Args:
            resource_type: The FHIR resource type class
            params: Search parameters (e.g., {"name": "Smith", "active": "true"})
            source: Source name to search in (uses first available if None)
            add_provenance: If True, automatically add provenance metadata to resources
            provenance_tag: Optional tag code for provenance (e.g., "aggregated", "transformed")
            follow_pagination: If True, automatically fetch all pages
            max_pages: Maximum number of pages to fetch (None for unlimited)

        Returns:
            Bundle containing search results

        Raises:
            ValueError: If source is invalid
            FHIRConnectionError: If connection fails

        Example:
            # Basic search
            bundle = await fhir_gateway.search(Patient, {"name": "Smith"}, "epic")

            # Search with automatic provenance
            bundle = await fhir_gateway.search(
                Condition,
                {"patient": "123"},
                "epic",
                add_provenance=True,
                provenance_tag="aggregated"
            )
        """
        bundle = await self._execute_with_client(
            "search",
            source=source,
            resource_type=resource_type,
            client_args=(resource_type,),
            client_kwargs={"params": params},
        )

        # Handle pagination if requested
        if follow_pagination:
            all_entries = bundle.entry or []
            page_count = 1

            while bundle.link:
                next_link = next(
                    (link for link in bundle.link if link.relation == "next"), None
                )
                if not next_link or (max_pages and page_count >= max_pages):
                    break

                # Extract the relative URL from the next link
                # next_url = next_link.url.split("/")[-2:]  # Get resource_type/_search part
                next_params = dict(
                    pair.split("=") for pair in next_link.url.split("?")[1].split("&")
                )

                bundle = await self._execute_with_client(
                    "search",
                    source=source,
                    resource_type=resource_type,
                    client_args=(resource_type, next_params),
                )

                if bundle.entry:
                    all_entries.extend(bundle.entry)
                page_count += 1

            bundle.entry = all_entries

        if add_provenance and bundle.entry:
            source_name = source or next(iter(self.connection_manager.sources.keys()))
            for entry in bundle.entry:
                if entry.resource:
                    entry.resource = add_provenance_metadata(
                        entry.resource,
                        source_name,
                        provenance_tag,
                        provenance_tag.capitalize() if provenance_tag else None,
                    )

        # Emit search event with result count
        type_name = resource_type.__resource_type__
        event_data = {
            "result_count": len(bundle.entry) if bundle.entry else 0,
        }
        # Do not include full params.
        self._emit_fhir_event("search", type_name, None, event_data)
        logger.info(
            f"FHIR operation: search on {type_name}, found {event_data['result_count']} results"
        )

        return bundle

    async def create(self, resource: Resource, source: str = None) -> Resource:
        """
        Create a new FHIR resource.

        Args:
            resource: The FHIR resource to create
            source: Source name to create in (uses first available if None)

        Returns:
            The created FHIR resource with server-assigned ID

        Raises:
            ValueError: If source is invalid
            FHIRConnectionError: If connection fails

        Example:
            # Create a new patient
            patient = Patient(name=[HumanName(family="Smith", given=["John"])])
            created = await fhir_gateway.create(patient, "epic")
            print(f"Created patient with ID: {created.id}")
        """
        created = await self._execute_with_client(
            "create",
            source=source,
            resource_type=resource.__class__,
            client_args=(resource,),
        )

        # Emit create event
        type_name = resource.__resource_type__
        self._emit_fhir_event("create", type_name, created.id, created)
        logger.debug(f"Created {type_name} resource with ID {created.id}")

        return created

    async def update(self, resource: Resource, source: str = None) -> Resource:
        """
        Update an existing FHIR resource.

        Args:
            resource: The FHIR resource to update (must have ID)
            source: Source name to update in (uses first available if None)

        Returns:
            The updated FHIR resource

        Raises:
            ValueError: If resource has no ID or source is invalid
            FHIRConnectionError: If connection fails

        Example:
            # Update a patient's name
            patient = await fhir_gateway.read(Patient, "123", "epic")
            patient.name[0].family = "Jones"
            updated = await fhir_gateway.update(patient, "epic")
        """
        if not resource.id:
            raise ValueError("Resource must have an ID for update")

        updated = await self._execute_with_client(
            "update",
            source=source,
            resource_type=resource.__class__,
            resource_id=resource.id,
            client_args=(resource,),
        )

        # Emit update event
        type_name = resource.__resource_type__
        self._emit_fhir_event("update", type_name, resource.id, updated)
        logger.debug(f"Updated {type_name} resource with ID {resource.id}")

        return updated

    async def delete(
        self, resource_type: Type[Resource], fhir_id: str, source: str = None
    ) -> bool:
        """
        Delete a FHIR resource.

        Args:
            resource_type: The FHIR resource type class
            fhir_id: Resource ID to delete
            source: Source name to delete from (uses first available if None)

        Returns:
            True if deletion was successful

        Raises:
            ValueError: If source is invalid
            FHIRConnectionError: If connection fails

        Example:
            # Delete a patient
            success = await fhir_gateway.delete(Patient, "123", "epic")
            if success:
                print("Patient deleted successfully")
        """
        success = await self._execute_with_client(
            "delete",
            source=source,
            resource_type=resource_type,
            resource_id=fhir_id,
            client_args=(resource_type, fhir_id),
        )

        if success:
            # Emit delete event
            type_name = resource_type.__resource_type__
            self._emit_fhir_event("delete", type_name, fhir_id, None)
            logger.debug(f"Deleted {type_name} resource with ID {fhir_id}")

        return success

    async def transaction(self, bundle: Bundle, source: str = None) -> Bundle:
        """
        Execute a FHIR transaction bundle.

        Args:
            bundle: The transaction bundle to execute
            source: Source name to execute in (uses first available if None)

        Returns:
            The response bundle with results

        Raises:
            ValueError: If source is invalid
            FHIRConnectionError: If connection fails

        Example:
            # Create a transaction bundle
            bundle = Bundle(type="transaction", entry=[
                BundleEntry(resource=patient1, request=BundleRequest(method="POST")),
                BundleEntry(resource=patient2, request=BundleRequest(method="POST"))
            ])
            result = await fhir_gateway.transaction(bundle, "epic")
        """
        result = await self._execute_with_client(
            "transaction",
            source=source,
            resource_type=Bundle,
            client_args=(bundle,),
        )

        # Emit transaction event with entry counts
        event_data = {
            "entry_count": len(bundle.entry) if bundle.entry else 0,
            "result_count": len(result.entry) if result.entry else 0,
        }
        self._emit_fhir_event("transaction", "Bundle", None, event_data)
        logger.debug(
            f"Executed transaction bundle with {len(bundle.entry) if bundle.entry else 0} entries"
        )

        return result

    @asynccontextmanager
    async def modify(
        self, resource_type: Type[Resource], fhir_id: str = None, source: str = None
    ):
        """
        Context manager for working with FHIR resources.

        Automatically handles fetching, updating, and error handling using connection pooling.

        Args:
            resource_type: The FHIR resource type class (e.g. Patient)
            fhir_id: Resource ID (if None, creates a new resource)
            source: Source name to use (uses first available if None)

        Yields:
            Resource: The FHIR resource object

        Raises:
            FHIRConnectionError: If connection fails
            ValueError: If resource type is invalid
        """
        client = await self.get_client(source)
        resource = None
        is_new = fhir_id is None

        # Get type name for error messages
        type_name = resource_type.__resource_type__

        try:
            if is_new:
                resource = resource_type()
            else:
                resource = await client.read(resource_type, fhir_id)
                logger.debug(f"Retrieved {type_name}/{fhir_id} in modify context")
                self._emit_fhir_event("read", type_name, fhir_id, resource)

            yield resource

            if is_new:
                updated_resource = await client.create(resource)
            else:
                updated_resource = await client.update(resource)

            resource.id = updated_resource.id
            for field_name, field_value in updated_resource.model_dump(
                exclude_none=True
            ).items():
                if hasattr(resource, field_name):
                    setattr(resource, field_name, field_value)

            operation = "create" if is_new else "update"
            self._emit_fhir_event(operation, type_name, resource.id, updated_resource)
            logger.debug(
                f"{'Created' if is_new else 'Updated'} {type_name} resource in modify context"
            )

        except Exception as e:
            operation = (
                "read"
                if not is_new and resource is None
                else "create"
                if is_new
                else "update"
            )
            FHIRErrorHandler.handle_fhir_error(e, type_name, fhir_id, operation)

    async def _execute_with_client(
        self,
        operation: str,
        *,  # Force keyword-only arguments
        source: str = None,
        resource_type: Type[Resource] = None,
        resource_id: str = None,
        client_args: tuple = (),
        client_kwargs: dict = None,
    ):
        """
        Execute a client operation with consistent error handling.

        Args:
            operation: Operation name (read, create, update, delete, etc.)
            source: Source name to use
            resource_type: Resource type for error handling
            resource_id: Resource ID for error handling (if applicable)
            client_args: Positional arguments to pass to the client method
            client_kwargs: Keyword arguments to pass to the client method
        """
        client = await self.get_client(source)
        client_kwargs = client_kwargs or {}

        try:
            result = await getattr(client, operation)(*client_args, **client_kwargs)
            return result

        except Exception as e:
            # Use existing error handler
            error_resource_type = resource_type or (
                client_args[0].__class__
                if client_args and hasattr(client_args[0], "__class__")
                else None
            )
            FHIRErrorHandler.handle_fhir_error(
                e, error_resource_type, resource_id, operation
            )

    def _emit_fhir_event(
        self, operation: str, resource_type: str, resource_id: str, resource: Any = None
    ):
        """
        Emit an event for FHIR operations.

        Args:
            operation: The FHIR operation (read, search, create, update, delete)
            resource_type: The FHIR resource type
            resource_id: The resource ID
            resource: The resource object or data
        """
        if not self.use_events:
            return

        self.events.emit_event(
            create_fhir_event,
            operation,
            resource_type,
            resource_id,
            resource,
            use_events=self.use_events,
        )
