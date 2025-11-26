"""FHIR utilities for HealthChain."""

from healthchain.fhir.helpers import (
    create_condition,
    create_medication_statement,
    create_allergy_intolerance,
    create_single_codeable_concept,
    create_single_reaction,
    set_condition_category,
    read_content_attachment,
    create_document_reference,
    create_single_attachment,
    create_resource_from_dict,
    convert_prefetch_to_fhir_objects,
    add_provenance_metadata,
    add_coding_to_codeable_concept,
)

from healthchain.fhir.bundle_helpers import (
    create_bundle,
    add_resource,
    get_resources,
    set_resources,
    merge_bundles,
    extract_resources,
    count_resources,
)

from healthchain.fhir.converters import (
    BundleConverterConfig,
    bundle_to_dataframe,
    get_supported_resources,
    get_resource_info,
    print_supported_resources,
)

__all__ = [
    # Resource creation
    "create_condition",
    "create_medication_statement",
    "create_allergy_intolerance",
    "create_single_codeable_concept",
    "create_single_reaction",
    "set_condition_category",
    "read_content_attachment",
    "create_document_reference",
    "create_single_attachment",
    "create_resource_from_dict",
    "convert_prefetch_to_fhir_objects",
    # Resource modification
    "add_provenance_metadata",
    "add_coding_to_codeable_concept",
    # Bundle operations
    "create_bundle",
    "add_resource",
    "get_resources",
    "set_resources",
    "merge_bundles",
    "extract_resources",
    "count_resources",
    # Bundle to DataFrame conversion
    "BundleConverterConfig",
    "bundle_to_dataframe",
    "get_supported_resources",
    "get_resource_info",
    "print_supported_resources",
]
