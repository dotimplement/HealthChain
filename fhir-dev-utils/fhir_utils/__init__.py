"""
FHIR Development Utilities - Core Module

Type-safe FHIR resource creation, validation, and manipulation tools
for accelerating healthcare application development.
"""

from .resource_factory import (
    ResourceFactory,
    PatientBuilder,
    ConditionBuilder,
    ObservationBuilder,
    MedicationStatementBuilder,
    AllergyIntoleranceBuilder,
    DocumentReferenceBuilder,
)
from .validators import (
    FHIRValidator,
    ValidationResult,
    validate_resource,
    validate_bundle,
    check_required_fields,
    validate_references,
)
from .bundle_tools import (
    BundleBuilder,
    BundleAnalyzer,
    create_transaction_bundle,
    create_collection_bundle,
    merge_bundles_smart,
    extract_by_type,
    find_by_reference,
)
from .converters import (
    FHIRConverter,
    bundle_to_flat_dict,
    dict_to_resource,
    resources_to_dataframe,
    dataframe_to_resources,
)

__all__ = [
    # Resource Factory
    "ResourceFactory",
    "PatientBuilder",
    "ConditionBuilder",
    "ObservationBuilder",
    "MedicationStatementBuilder",
    "AllergyIntoleranceBuilder",
    "DocumentReferenceBuilder",
    # Validators
    "FHIRValidator",
    "ValidationResult",
    "validate_resource",
    "validate_bundle",
    "check_required_fields",
    "validate_references",
    # Bundle Tools
    "BundleBuilder",
    "BundleAnalyzer",
    "create_transaction_bundle",
    "create_collection_bundle",
    "merge_bundles_smart",
    "extract_by_type",
    "find_by_reference",
    # Converters
    "FHIRConverter",
    "bundle_to_flat_dict",
    "dict_to_resource",
    "resources_to_dataframe",
    "dataframe_to_resources",
]
