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
]
