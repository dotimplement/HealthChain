"""
FHIR Bundle Manipulation Tools

Provides utilities for creating, analyzing, and manipulating
FHIR Bundles with type safety and convenience methods.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Type, Iterator, Set
from collections import defaultdict

from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.observation import Observation
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance


def _generate_id(prefix: str = "bundle") -> str:
    """Generate a unique ID."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class BundleBuilder:
    """
    Builder for creating FHIR Bundles with a fluent interface.

    Example:
        bundle = BundleBuilder() \\
            .as_transaction() \\
            .add(patient) \\
            .add(condition, method="POST") \\
            .build()
    """

    def __init__(self):
        self._type = "collection"
        self._entries: List[Dict[str, Any]] = []
        self._id = _generate_id()
        self._timestamp: Optional[str] = None
        self._identifier: Optional[Dict[str, Any]] = None

    def with_id(self, bundle_id: str) -> "BundleBuilder":
        """Set custom bundle ID."""
        self._id = bundle_id
        return self

    def with_timestamp(self, timestamp: Optional[datetime] = None) -> "BundleBuilder":
        """Set bundle timestamp."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        self._timestamp = timestamp.isoformat() + "Z"
        return self

    def with_identifier(
        self,
        value: str,
        system: Optional[str] = None
    ) -> "BundleBuilder":
        """Set bundle identifier."""
        self._identifier = {"value": value}
        if system:
            self._identifier["system"] = system
        return self

    def as_collection(self) -> "BundleBuilder":
        """Set bundle type to collection."""
        self._type = "collection"
        return self

    def as_transaction(self) -> "BundleBuilder":
        """Set bundle type to transaction."""
        self._type = "transaction"
        return self

    def as_batch(self) -> "BundleBuilder":
        """Set bundle type to batch."""
        self._type = "batch"
        return self

    def as_document(self) -> "BundleBuilder":
        """Set bundle type to document."""
        self._type = "document"
        return self

    def as_searchset(self) -> "BundleBuilder":
        """Set bundle type to searchset."""
        self._type = "searchset"
        return self

    def add(
        self,
        resource: Union[Resource, Dict[str, Any]],
        method: Optional[str] = None,
        url: Optional[str] = None,
        full_url: Optional[str] = None,
        if_match: Optional[str] = None,
        if_none_exist: Optional[str] = None
    ) -> "BundleBuilder":
        """
        Add a resource to the bundle.

        Args:
            resource: FHIR resource to add
            method: HTTP method for transaction/batch (POST, PUT, DELETE)
            url: Request URL for transaction/batch
            full_url: Full URL for the entry
            if_match: ETag for conditional update
            if_none_exist: Query for conditional create

        Returns:
            Self for chaining
        """
        entry: Dict[str, Any] = {}

        # Handle resource
        if isinstance(resource, dict):
            entry["resource"] = resource
            res_type = resource.get("resourceType")
            res_id = resource.get("id")
        else:
            entry["resource"] = resource.model_dump(exclude_none=True)
            res_type = resource.resource_type
            res_id = getattr(resource, "id", None)

        # Set fullUrl
        if full_url:
            entry["fullUrl"] = full_url
        elif res_id:
            entry["fullUrl"] = f"urn:uuid:{res_id}" if res_id.startswith("urn:") else f"{res_type}/{res_id}"

        # Add request for transaction/batch
        if self._type in ("transaction", "batch") or method:
            request: Dict[str, Any] = {}

            if method:
                request["method"] = method.upper()
            elif self._type == "transaction":
                request["method"] = "POST" if not res_id else "PUT"

            if url:
                request["url"] = url
            elif res_type:
                if request.get("method") in ("PUT", "DELETE") and res_id:
                    request["url"] = f"{res_type}/{res_id}"
                else:
                    request["url"] = res_type

            if if_match:
                request["ifMatch"] = if_match
            if if_none_exist:
                request["ifNoneExist"] = if_none_exist

            if request:
                entry["request"] = request

        self._entries.append(entry)
        return self

    def add_all(
        self,
        resources: List[Union[Resource, Dict[str, Any]]],
        method: Optional[str] = None
    ) -> "BundleBuilder":
        """Add multiple resources to the bundle."""
        for resource in resources:
            self.add(resource, method=method)
        return self

    def build(self) -> Bundle:
        """Build and return the Bundle."""
        bundle_data = {
            "resourceType": "Bundle",
            "id": self._id,
            "type": self._type,
            "entry": self._entries
        }

        if self._timestamp:
            bundle_data["timestamp"] = self._timestamp

        if self._identifier:
            bundle_data["identifier"] = self._identifier

        bundle_data["total"] = len(self._entries)

        return Bundle(**bundle_data)


class BundleAnalyzer:
    """
    Utility class for analyzing and querying FHIR Bundles.

    Example:
        analyzer = BundleAnalyzer(bundle)
        patients = analyzer.get_resources(Patient)
        conditions = analyzer.get_resources_for_patient("patient-123", Condition)
    """

    def __init__(self, bundle: Union[Bundle, Dict[str, Any]]):
        """
        Initialize analyzer with a bundle.

        Args:
            bundle: FHIR Bundle to analyze
        """
        if isinstance(bundle, dict):
            self._bundle = Bundle(**bundle)
        else:
            self._bundle = bundle

        self._index: Dict[str, Dict[str, Any]] = {}
        self._by_type: Dict[str, List[Any]] = defaultdict(list)
        self._patient_resources: Dict[str, List[Any]] = defaultdict(list)

        self._build_index()

    def _build_index(self) -> None:
        """Build internal indices for fast lookup."""
        entries = self._bundle.entry or []

        for entry in entries:
            resource = entry.resource
            if not resource:
                continue

            res_type = resource.resource_type
            res_id = getattr(resource, "id", None)

            # Index by type
            self._by_type[res_type].append(resource)

            # Index by reference
            if res_id:
                ref_key = f"{res_type}/{res_id}"
                self._index[ref_key] = resource

            # Index by patient reference
            patient_ref = self._get_patient_reference(resource)
            if patient_ref:
                self._patient_resources[patient_ref].append(resource)

    def _get_patient_reference(self, resource: Resource) -> Optional[str]:
        """Extract patient reference from a resource."""
        # Try common fields that reference patients
        for field in ["subject", "patient"]:
            ref = getattr(resource, field, None)
            if ref and hasattr(ref, "reference"):
                return ref.reference
        return None

    @property
    def total(self) -> int:
        """Total number of entries in the bundle."""
        return len(self._bundle.entry or [])

    @property
    def resource_types(self) -> List[str]:
        """List of resource types in the bundle."""
        return list(self._by_type.keys())

    def get_resource_counts(self) -> Dict[str, int]:
        """Get count of resources by type."""
        return {k: len(v) for k, v in self._by_type.items()}

    def get_resources(
        self,
        resource_type: Union[Type[Resource], str]
    ) -> List[Resource]:
        """
        Get all resources of a specific type.

        Args:
            resource_type: Resource class or type name string

        Returns:
            List of matching resources
        """
        if isinstance(resource_type, type):
            type_name = resource_type.__name__
        else:
            type_name = resource_type

        return list(self._by_type.get(type_name, []))

    def get_resource_by_id(
        self,
        resource_type: Union[Type[Resource], str],
        resource_id: str
    ) -> Optional[Resource]:
        """
        Get a specific resource by type and ID.

        Args:
            resource_type: Resource class or type name
            resource_id: Resource ID

        Returns:
            Resource if found, None otherwise
        """
        if isinstance(resource_type, type):
            type_name = resource_type.__name__
        else:
            type_name = resource_type

        return self._index.get(f"{type_name}/{resource_id}")

    def get_resource_by_reference(self, reference: str) -> Optional[Resource]:
        """
        Get a resource by its reference string.

        Args:
            reference: Reference string (e.g., "Patient/123")

        Returns:
            Resource if found, None otherwise
        """
        return self._index.get(reference)

    def get_resources_for_patient(
        self,
        patient_ref: str,
        resource_type: Optional[Union[Type[Resource], str]] = None
    ) -> List[Resource]:
        """
        Get all resources associated with a patient.

        Args:
            patient_ref: Patient reference (e.g., "Patient/123")
            resource_type: Optional filter by resource type

        Returns:
            List of resources for the patient
        """
        # Normalize reference format
        if not patient_ref.startswith("Patient/"):
            patient_ref = f"Patient/{patient_ref}"

        resources = self._patient_resources.get(patient_ref, [])

        if resource_type:
            if isinstance(resource_type, type):
                type_name = resource_type.__name__
            else:
                type_name = resource_type
            resources = [r for r in resources if r.resource_type == type_name]

        return resources

    def find_resources(
        self,
        predicate: callable
    ) -> List[Resource]:
        """
        Find resources matching a predicate function.

        Args:
            predicate: Function(resource) -> bool

        Returns:
            List of matching resources
        """
        results = []
        for entry in self._bundle.entry or []:
            if entry.resource and predicate(entry.resource):
                results.append(entry.resource)
        return results

    def iter_resources(self) -> Iterator[Resource]:
        """Iterate over all resources in the bundle."""
        for entry in self._bundle.entry or []:
            if entry.resource:
                yield entry.resource

    def to_summary(self) -> Dict[str, Any]:
        """Get a summary of the bundle contents."""
        return {
            "bundle_id": self._bundle.id,
            "bundle_type": self._bundle.type,
            "total_entries": self.total,
            "resource_counts": self.get_resource_counts(),
            "patient_count": len(self.get_resources("Patient")),
            "resource_types": self.resource_types
        }


def create_transaction_bundle(
    resources: List[Union[Resource, Dict[str, Any]]],
    default_method: str = "POST"
) -> Bundle:
    """
    Create a transaction bundle from a list of resources.

    Args:
        resources: List of FHIR resources
        default_method: Default HTTP method (POST, PUT)

    Returns:
        Transaction Bundle
    """
    builder = BundleBuilder().as_transaction()
    for resource in resources:
        builder.add(resource, method=default_method)
    return builder.build()


def create_collection_bundle(
    resources: List[Union[Resource, Dict[str, Any]]]
) -> Bundle:
    """
    Create a collection bundle from a list of resources.

    Args:
        resources: List of FHIR resources

    Returns:
        Collection Bundle
    """
    builder = BundleBuilder().as_collection()
    for resource in resources:
        builder.add(resource)
    return builder.build()


def merge_bundles_smart(
    bundles: List[Union[Bundle, Dict[str, Any]]],
    deduplicate: bool = True,
    bundle_type: str = "collection"
) -> Bundle:
    """
    Merge multiple bundles into one with smart deduplication.

    Args:
        bundles: List of bundles to merge
        deduplicate: Remove duplicate resources
        bundle_type: Type of resulting bundle

    Returns:
        Merged Bundle
    """
    builder = BundleBuilder()

    # Set bundle type
    type_setters = {
        "collection": builder.as_collection,
        "transaction": builder.as_transaction,
        "batch": builder.as_batch,
        "searchset": builder.as_searchset,
    }
    type_setters.get(bundle_type, builder.as_collection)()

    seen_refs: Set[str] = set()

    for bundle in bundles:
        if isinstance(bundle, dict):
            entries = bundle.get("entry", [])
        else:
            entries = bundle.entry or []

        for entry in entries:
            if isinstance(entry, dict):
                resource = entry.get("resource", {})
                res_type = resource.get("resourceType")
                res_id = resource.get("id")
            else:
                resource = entry.resource
                if resource:
                    res_type = resource.resource_type
                    res_id = getattr(resource, "id", None)
                else:
                    continue

            # Check for duplicates
            if deduplicate and res_id:
                ref_key = f"{res_type}/{res_id}"
                if ref_key in seen_refs:
                    continue
                seen_refs.add(ref_key)

            builder.add(resource)

    return builder.build()


def extract_by_type(
    bundle: Union[Bundle, Dict[str, Any]],
    resource_type: Union[Type[Resource], str],
    remove: bool = False
) -> List[Resource]:
    """
    Extract resources of a specific type from a bundle.

    Args:
        bundle: Source bundle
        resource_type: Type to extract
        remove: If True, modify bundle in place (only for Bundle objects)

    Returns:
        List of extracted resources
    """
    analyzer = BundleAnalyzer(bundle)
    return analyzer.get_resources(resource_type)


def find_by_reference(
    bundle: Union[Bundle, Dict[str, Any]],
    reference: str
) -> Optional[Resource]:
    """
    Find a resource by reference in a bundle.

    Args:
        bundle: Bundle to search
        reference: Reference string (e.g., "Patient/123")

    Returns:
        Resource if found, None otherwise
    """
    analyzer = BundleAnalyzer(bundle)
    return analyzer.get_resource_by_reference(reference)


def split_bundle_by_patient(
    bundle: Union[Bundle, Dict[str, Any]]
) -> Dict[str, Bundle]:
    """
    Split a bundle into separate bundles per patient.

    Args:
        bundle: Bundle containing resources for multiple patients

    Returns:
        Dict mapping patient ID to their bundle
    """
    analyzer = BundleAnalyzer(bundle)
    patients = analyzer.get_resources("Patient")

    result: Dict[str, Bundle] = {}

    for patient in patients:
        patient_id = getattr(patient, "id", None)
        if not patient_id:
            continue

        patient_ref = f"Patient/{patient_id}"
        patient_resources = analyzer.get_resources_for_patient(patient_ref)

        builder = BundleBuilder().as_collection()
        builder.add(patient)
        for resource in patient_resources:
            if resource.resource_type != "Patient":
                builder.add(resource)

        result[patient_id] = builder.build()

    return result
