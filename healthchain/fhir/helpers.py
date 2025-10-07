"""Convenience functions for creating minimal FHIR resources."""

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


def set_problem_list_item_category(condition: Condition) -> Condition:
    """Set the category of a FHIR Condition to problem-list-item.

    Sets the category field of a FHIR Condition resource to indicate it is a problem list item.
    This is commonly used to distinguish conditions that are part of the patient's active
    problem list from other types of conditions (e.g. encounter-diagnosis).

    Args:
        condition: The FHIR Condition resource to modify

    Returns:
        Condition: The modified FHIR Condition resource with problem-list-item category set
    """
    condition.category = [
        create_single_codeable_concept(
            code="problem-list-item",
            display="Problem List Item",
            system="http://terminology.hl7.org/CodeSystem/condition-category",
        )
    ]
    return condition


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
    **kwargs
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
