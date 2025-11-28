"""Convenience functions for creating minimal FHIR resources.
Patterns:
- create_*(): create a new FHIR resource with sensible defaults - useful for dev, use with caution
- add_*(): add data to resources with list fields safely (e.g. coding)
- set_*(): set the field of specific resources with soft validation (e.g. category)
- read_*(): return a human readable format of the data in a resource (e.g. attachments)
"""

import logging
import base64
import datetime
import uuid
import importlib

from typing import Optional, List, Dict, Any
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.documentreference import DocumentReference
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.attachment import Attachment
from fhir.resources.resource import Resource
from fhir.resources.reference import Reference
from fhir.resources.meta import Meta


logger = logging.getLogger(__name__)


def _generate_id() -> str:
    """Generate a unique ID prefixed with 'hc-'.

    Returns:
        str: A unique ID string prefixed with 'hc-'
    """
    return f"hc-{str(uuid.uuid4())}"


def create_resource_from_dict(
    resource_dict: Dict, resource_type: str
) -> Optional[Resource]:
    """Create a FHIR resource instance from a dictionary

    Args:
        resource_dict: Dictionary representation of the resource
        resource_type: Type of FHIR resource to create

    Returns:
        Optional[Resource]: FHIR resource instance or None if creation failed
    """
    try:
        resource_module = importlib.import_module(
            f"fhir.resources.{resource_type.lower()}"
        )
        resource_class = getattr(resource_module, resource_type)
        return resource_class(**resource_dict)
    except Exception as e:
        logger.error(f"Failed to create FHIR resource: {str(e)}")
        return None


def convert_prefetch_to_fhir_objects(
    prefetch_dict: Dict[str, Any],
) -> Dict[str, Resource]:
    """Convert a dictionary of FHIR resource dicts to FHIR Resource objects.

    Takes a prefetch dictionary where values may be either dict representations of FHIR
    resources or already instantiated FHIR Resource objects, and ensures all values are
    FHIR Resource objects.

    Args:
        prefetch_dict: Dictionary mapping keys to FHIR resource dicts or objects

    Returns:
        Dict[str, Resource]: Dictionary with same keys but all values as FHIR Resource objects

    Example:
        >>> prefetch = {
        ...     "patient": {"resourceType": "Patient", "id": "123"},
        ...     "condition": Condition(id="456", ...)
        ... }
        >>> fhir_objects = convert_prefetch_to_fhir_objects(prefetch)
        >>> isinstance(fhir_objects["patient"], Patient)  # True
        >>> isinstance(fhir_objects["condition"], Condition)  # True
    """
    from fhir.resources import get_fhir_model_class

    result: Dict[str, Resource] = {}

    for key, resource_data in prefetch_dict.items():
        if isinstance(resource_data, dict):
            # Convert dict to FHIR Resource object
            resource_type = resource_data.get("resourceType")
            if resource_type:
                try:
                    resource_class = get_fhir_model_class(resource_type)
                    result[key] = resource_class(**resource_data)
                except Exception as e:
                    logger.warning(
                        f"Failed to convert {resource_type} to FHIR object: {e}"
                    )
                    result[key] = resource_data
            else:
                logger.warning(
                    f"No resourceType found for key '{key}', keeping as dict"
                )
                result[key] = resource_data
        elif isinstance(resource_data, Resource):
            # Already a FHIR object
            result[key] = resource_data
        else:
            logger.warning(f"Unexpected type for key '{key}': {type(resource_data)}")
            result[key] = resource_data

    return result


def create_single_codeable_concept(
    code: str,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
) -> CodeableConcept:
    """
    Create a minimal FHIR CodeableConcept with a single coding.

    Args:
        code: REQUIRED. The code value from the code system
        display: The display name for the code
        system: The code system (default: SNOMED CT)

    Returns:
        CodeableConcept: A FHIR CodeableConcept resource with a single coding
    """
    return CodeableConcept(coding=[Coding(system=system, code=code, display=display)])


def create_single_reaction(
    code: str,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
    severity: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Create a minimal FHIR Reaction with a single coding.

    Creates a FHIR Reaction object with a single manifestation coding. The manifestation
    describes the clinical reaction that was observed. The severity indicates how severe
    the reaction was.

    Args:
        code: REQUIRED. The code value from the code system representing the reaction manifestation
        display: The display name for the manifestation code
        system: The code system for the manifestation code (default: SNOMED CT)
        severity: The severity of the reaction (mild, moderate, severe)

    Returns:
        A list containing a single FHIR Reaction dictionary with manifestation and severity fields
    """
    return [
        {
            "manifestation": [
                CodeableReference(
                    concept=CodeableConcept(
                        coding=[Coding(system=system, code=code, display=display)]
                    )
                )
            ],
            "severity": severity,
        }
    ]


def create_single_attachment(
    content_type: Optional[str] = None,
    data: Optional[str] = None,
    url: Optional[str] = None,
    title: Optional[str] = "Attachment created by HealthChain",
) -> Attachment:
    """Create a minimal FHIR Attachment.

    Creates a FHIR Attachment resource with basic fields. Either data or url should be provided.
    If data is provided, it will be base64 encoded.

    Args:
        content_type: The MIME type of the content
        data: The actual data content to be base64 encoded
        url: The URL where the data can be found
        title: A title for the attachment (default: "Attachment created by HealthChain")

    Returns:
        Attachment: A FHIR Attachment resource with basic metadata and content
    """

    if not data and not url:
        logger.warning("No data or url provided for attachment")

    if data:
        data = base64.b64encode(data.encode("utf-8")).decode("utf-8")

    return Attachment(
        contentType=content_type,
        data=data,
        url=url,
        title=title,
        creation=datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        ),
    )


def create_condition(
    subject: str,
    clinical_status: str = "active",
    code: Optional[str] = None,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
) -> Condition:
    """
    Create a minimal active FHIR Condition.
    If you need to create a more complex condition, use the FHIR Condition resource directly.
    https://build.fhir.org/condition.html

    Args:
        subject: REQUIRED. Reference to the patient (e.g. "Patient/123")
        clinical_status: REQUIRED. Clinical status (default: active)
        code: The condition code
        display: The display name for the condition
        system: The code system (default: SNOMED CT)

    Returns:
        Condition: A FHIR Condition resource with an auto-generated ID prefixed with 'hc-'
    """
    if code:
        condition_code = create_single_codeable_concept(code, display, system)
    else:
        condition_code = None

    condition = Condition(
        id=_generate_id(),
        subject=Reference(reference=subject),
        clinicalStatus=create_single_codeable_concept(
            code=clinical_status,
            display=clinical_status.capitalize(),
            system="http://terminology.hl7.org/CodeSystem/condition-clinical",
        ),
        code=condition_code,
    )

    return condition


def create_medication_statement(
    subject: str,
    status: Optional[str] = "recorded",
    code: Optional[str] = None,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
) -> MedicationStatement:
    """
    Create a minimal recorded FHIR MedicationStatement.
    If you need to create a more complex medication statement, use the FHIR MedicationStatement resource directly.
    https://build.fhir.org/medicationstatement.html

    Args:
        subject: REQUIRED. Reference to the patient (e.g. "Patient/123")
        status: REQUIRED. Status of the medication (default: recorded)
        code: The medication code
        display: The display name for the medication
        system: The code system (default: SNOMED CT)

    Returns:
        MedicationStatement: A FHIR MedicationStatement resource with an auto-generated ID prefixed with 'hc-'
    """
    if code:
        medication_concept = create_single_codeable_concept(code, display, system)
    else:
        medication_concept = None

    medication = MedicationStatement(
        id=_generate_id(),
        subject=Reference(reference=subject),
        status=status,
        medication={"concept": medication_concept},
    )

    return medication


def create_allergy_intolerance(
    patient: str,
    code: Optional[str] = None,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
) -> AllergyIntolerance:
    """
    Create a minimal active FHIR AllergyIntolerance.
    If you need to create a more complex allergy intolerance, use the FHIR AllergyIntolerance resource directly.
    https://build.fhir.org/allergyintolerance.html

    Args:
        patient: REQUIRED. Reference to the patient (e.g. "Patient/123")
        code: The allergen code
        display: The display name for the allergen
        system: The code system (default: SNOMED CT)

    Returns:
        AllergyIntolerance: A FHIR AllergyIntolerance resource with an auto-generated ID prefixed with 'hc-'
    """
    if code:
        allergy_code = create_single_codeable_concept(code, display, system)
    else:
        allergy_code = None

    allergy = AllergyIntolerance(
        id=_generate_id(),
        patient=Reference(reference=patient),
        code=allergy_code,
    )

    return allergy


def create_document_reference(
    data: Optional[Any] = None,
    url: Optional[str] = None,
    content_type: Optional[str] = None,
    status: str = "current",
    description: Optional[str] = "DocumentReference created by HealthChain",
    attachment_title: Optional[str] = "Attachment created by HealthChain",
) -> DocumentReference:
    """
    Create a minimal FHIR DocumentReference.
    If you need to create a more complex document reference, use the FHIR DocumentReference resource directly.
    https://build.fhir.org/documentreference.html

    Args:
        data: The data content of the document attachment
        url: URL where the document can be accessed
        content_type: MIME type of the document (e.g. "application/pdf", "text/xml", "image/png")
        status: REQUIRED. Status of the document reference (default: current)
        description: Description of the document reference
        attachment_title: Title for the document attachment

    Returns:
        DocumentReference: A FHIR DocumentReference resource with an auto-generated ID prefixed with 'hc-'
    """
    document_reference = DocumentReference(
        id=_generate_id(),
        status=status,
        date=datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        ),
        description=description,
        content=[
            {
                "attachment": create_single_attachment(
                    content_type=content_type,
                    data=data,
                    url=url,
                    title=attachment_title,
                )
            }
        ],
    )

    return document_reference


def create_document_reference_content(
    attachment_data: Optional[str] = None,
    url: Optional[str] = None,
    content_type: str = "text/plain",
    language: Optional[str] = "en-US",
    title: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create a FHIR DocumentReferenceContent object.

    Creates a DocumentReferenceContent structure that can be added to a DocumentReference.
    Either attachment_data or url must be provided. If attachment_data is provided, it will
    be base64 encoded automatically.

    Args:
        attachment_data: The content data (text that will be base64 encoded)
        url: URL where the content can be accessed
        content_type: MIME type (e.g., 'text/plain', 'text/html', 'application/pdf') (default: text/plain)
        language: Language code (default: en-US)
        title: Optional title for the content (default: "Attachment created by HealthChain")
        **kwargs: Additional DocumentReferenceContent fields (e.g., format, profile)

    Returns:
        Dict[str, Any]: A FHIR DocumentReferenceContent dictionary with attachment and optional language

    Example:
        >>> # Create content with inline data
        >>> content = create_document_reference_content(
        ...     attachment_data="Patient presents with fever...",
        ...     content_type="text/plain",
        ...     title="Clinical Note"
        ... )
        >>>
        >>> # Create content with URL reference
        >>> content = create_document_reference_content(
        ...     url="https://example.com/document.pdf",
        ...     content_type="application/pdf",
        ...     title="Lab Report"
        ... )
        >>>
        >>> # Add content to a DocumentReference
        >>> doc_ref = DocumentReference(
        ...     id="doc-1",
        ...     status="current",
        ...     content=[content]
        ... )
    """
    if not attachment_data and not url:
        logger.warning(
            "No attachment_data or url provided for DocumentReferenceContent"
        )

    if title is None:
        title = "Attachment created by HealthChain"

    attachment = create_single_attachment(
        content_type=content_type,
        data=attachment_data,
        url=url,
        title=title,
    )

    content: Dict[str, Any] = {
        "attachment": attachment,
    }

    if language:
        content["language"] = language

    content.update(kwargs)

    return content


def set_condition_category(condition: Condition, category: str) -> Condition:
    """
    Set the category of a FHIR Condition to either 'problem-list-item' or 'encounter-diagnosis'.

    Args:
        condition: The FHIR Condition resource to modify
        category: The category to set. Must be 'problem-list-item' or 'encounter-diagnosis'.

    Returns:
        Condition: The modified FHIR Condition resource with the specified category set

    Raises:
        ValueError: If the category is not one of the allowed values.
    """
    allowed_categories = {
        "problem-list-item": {
            "code": "problem-list-item",
            "display": "Problem List Item",
        },
        "encounter-diagnosis": {
            "code": "encounter-diagnosis",
            "display": "Encounter Diagnosis",
        },
    }
    if category not in allowed_categories:
        raise ValueError(
            f"Invalid category '{category}'. Must be one of: {list(allowed_categories.keys())}"
        )

    cat_info = allowed_categories[category]
    condition.category = [
        create_single_codeable_concept(
            code=cat_info["code"],
            display=cat_info["display"],
            system="http://terminology.hl7.org/CodeSystem/condition-category",
        )
    ]
    return condition


def add_provenance_metadata(
    resource: Resource,
    source: str,
    tag_code: Optional[str] = None,
    tag_display: Optional[str] = None,
) -> Resource:
    """Add provenance metadata to a FHIR resource.

    Adds source system identifier, timestamp, and optional processing tags to track
    data lineage and transformations for audit trails.

    Args:
        resource: The FHIR resource to annotate
        source: Name of the source system (e.g., "epic", "cerner")
        tag_code: Optional tag code for processing operations (e.g., "aggregated", "deduplicated")
        tag_display: Optional display text for the tag

    Returns:
        Resource: The resource with added provenance metadata

    Example:
        >>> condition = create_condition(subject="Patient/123", code="E11.9")
        >>> condition = add_provenance_metadata(condition, "epic", "aggregated", "Aggregated from source")
    """
    if not resource.meta:
        resource.meta = Meta()

    # Add source system identifier
    resource.meta.source = f"urn:healthchain:source:{source}"

    # Update timestamp
    resource.meta.lastUpdated = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Add processing tag if provided
    if tag_code:
        if not resource.meta.tag:
            resource.meta.tag = []

        resource.meta.tag.append(
            Coding(
                system="https://dotimplement.github.io/HealthChain/fhir/tags",
                code=tag_code,
                display=tag_display or tag_code,
            )
        )

    return resource


def add_coding_to_codeable_concept(
    codeable_concept: CodeableConcept,
    code: str,
    system: str,
    display: Optional[str] = None,
) -> CodeableConcept:
    """Add a coding to an existing CodeableConcept.

    Useful for adding standardized codes (e.g., SNOMED CT) to resources that already
    have codes from other systems (e.g., ICD-10).

    Args:
        codeable_concept: The CodeableConcept to add coding to
        code: The code value from the code system
        system: The code system URI
        display: Optional display text for the code

    Returns:
        CodeableConcept: The updated CodeableConcept with the new coding added

    Example:
        >>> # Add SNOMED CT code to a condition that has ICD-10
        >>> condition_code = condition.code
        >>> condition_code = add_coding_to_codeable_concept(
        ...     condition_code,
        ...     code="44054006",
        ...     system="http://snomed.info/sct",
        ...     display="Type 2 diabetes mellitus"
        ... )
    """
    if not codeable_concept.coding:
        codeable_concept.coding = []

    codeable_concept.coding.append(Coding(system=system, code=code, display=display))

    return codeable_concept


def read_content_attachment(
    document_reference: DocumentReference,
    include_data: bool = True,
) -> Optional[List[Dict[str, Any]]]:
    """Read the attachments in a human readable format from a FHIR DocumentReference content field.

    Args:
        document_reference: The FHIR DocumentReference resource
        include_data: Whether to include the data of the attachments. If true, the data will be also be decoded (default: True)

    Returns:
        Optional[List[Dict[str, Any]]]: List of dictionaries containing attachment data and metadata,
            or None if no attachments are found:
            [
                {
                    "data": str,
                    "metadata": Dict[str, Any]
                }
            ]
    """
    if not document_reference.content:
        return None

    attachments = []
    for content in document_reference.content:
        attachment = content.attachment
        result = {}

        if include_data:
            result["data"] = (
                attachment.url if attachment.url else attachment.data.decode("utf-8")
            )

        result["metadata"] = {
            "content_type": attachment.contentType,
            "title": attachment.title,
            "creation": attachment.creation,
        }

        attachments.append(result)

    return attachments
