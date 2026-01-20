"""FHIR utilities for HealthChain."""

from healthchain.fhir.version import (
    FHIRVersion,
    get_fhir_resource,
    get_default_version,
    set_default_version,
    reset_default_version,
    fhir_version_context,
    convert_resource,
    get_resource_version,
)

from healthchain.fhir.resourcehelpers import (
    create_condition,
    create_medication_statement,
    create_allergy_intolerance,
    create_value_quantity_observation,
    create_patient,
    create_risk_assessment_from_prediction,
    create_document_reference,
    create_document_reference_content,
    set_condition_category,
    add_provenance_metadata,
    add_coding_to_codeable_concept,
)

from healthchain.fhir.elementhelpers import (
    create_single_codeable_concept,
    create_single_reaction,
    create_single_attachment,
)

from healthchain.fhir.readers import (
    create_resource_from_dict,
    convert_prefetch_to_fhir_objects,
    prefetch_to_bundle,
    read_content_attachment,
)

from healthchain.fhir.bundlehelpers import (
    create_bundle,
    add_resource,
    get_resource_type,
    get_resources,
    set_resources,
    merge_bundles,
    extract_resources,
    count_resources,
)

from healthchain.fhir.dataframe import (
    BundleConverterConfig,
    bundle_to_dataframe,
    get_supported_resources,
    get_resource_info,
    print_supported_resources,
)

from healthchain.fhir.utilities import (
    calculate_age_from_birthdate,
    calculate_age_from_event_date,
    encode_gender,
)

__all__ = [
    # Version management
    "FHIRVersion",
    "get_fhir_resource",
    "get_default_version",
    "set_default_version",
    "reset_default_version",
    "fhir_version_context",
    "convert_resource",
    "get_resource_version",
    # Resource creation
    "create_condition",
    "create_medication_statement",
    "create_allergy_intolerance",
    "create_value_quantity_observation",
    "create_patient",
    "create_risk_assessment_from_prediction",
    "create_document_reference",
    "create_document_reference_content",
    # Element creation
    "create_single_codeable_concept",
    "create_single_reaction",
    "create_single_attachment",
    # Resource modification
    "set_condition_category",
    "add_provenance_metadata",
    "add_coding_to_codeable_concept",
    # Conversions and readers
    "create_resource_from_dict",
    "convert_prefetch_to_fhir_objects",
    "prefetch_to_bundle",
    "read_content_attachment",
    # Bundle operations
    "create_bundle",
    "add_resource",
    "get_resource_type",
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
    # Utility functions
    "calculate_age_from_birthdate",
    "calculate_age_from_event_date",
    "encode_gender",
]
