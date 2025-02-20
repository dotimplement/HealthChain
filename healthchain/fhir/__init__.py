"""FHIR utilities for HealthChain."""

from healthchain.fhir.helpers import (
    create_condition,
    create_medication_statement,
    create_allergy_intolerance,
    create_single_codeable_concept,
    create_single_reaction,
    set_problem_list_item_category,
    read_content_attachment,
    create_document_reference,
    create_single_attachment,
)

from healthchain.fhir.bundle_helpers import (
    create_bundle,
    add_resource,
    get_resources,
    set_resources,
)

__all__ = [
    # Resource creation
    "create_condition",
    "create_medication_statement",
    "create_allergy_intolerance",
    "create_single_codeable_concept",
    "create_single_reaction",
    "set_problem_list_item_category",
    "read_content_attachment",
    "create_document_reference",
    "create_single_attachment",
    # Bundle operations
    "create_bundle",
    "add_resource",
    "get_resources",
    "set_resources",
]
