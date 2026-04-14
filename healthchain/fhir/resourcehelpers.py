"""FHIR resource creation and modification functions.

This module provides convenience functions for creating and modifying FHIR resources.

Patterns:
- create_*(): create a new FHIR resource with sensible defaults
- set_*(): set specific fields of resources with soft validation
- add_*(): add data to resources safely

Parameters marked REQUIRED are required by FHIR specification.
"""

import logging
import datetime

from typing import List, Optional, Dict, Any

from fhir.resources.R4B.allergyintolerance import AllergyIntolerance
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.documentreference import DocumentReference
from fhir.resources.R4B.identifier import Identifier
from fhir.resources.R4B.medicationstatement import MedicationStatement
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.quantity import Quantity
from fhir.resources.R4B.reference import Reference
from fhir.resources.R4B.riskassessment import RiskAssessment
from fhir.resources.R4B.codeableconcept import CodeableConcept

from fhir.resources.R4B.auditevent import AuditEvent, AuditEventAgent, AuditEventSource
from fhir.resources.R4B.coding import Coding

from healthchain.fhir.elementhelpers import (
    create_single_codeable_concept,
    create_single_attachment,
)
from healthchain.fhir.utilities import _generate_id

logger = logging.getLogger(__name__)


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
    condition_code = (
        create_single_codeable_concept(code, display, system) if code else None
    )

    return Condition(
        id=_generate_id(),
        subject=Reference(reference=subject),
        clinicalStatus=create_single_codeable_concept(
            code=clinical_status,
            display=clinical_status.capitalize(),
            system="http://terminology.hl7.org/CodeSystem/condition-clinical",
        ),
        code=condition_code,
    )


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
    medication_concept = (
        create_single_codeable_concept(code, display, system) if code else None
    )

    return MedicationStatement(
        id=_generate_id(),
        subject=Reference(reference=subject),
        status=status,
        medicationCodeableConcept=medication_concept,
    )


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
    allergy_code = (
        create_single_codeable_concept(code, display, system) if code else None
    )

    return AllergyIntolerance(
        id=_generate_id(),
        patient=Reference(reference=patient),
        code=allergy_code,
    )


def create_value_quantity_observation(
    code: str,
    value: float,
    unit: str,
    status: str = "final",
    subject: Optional[str] = None,
    system: str = "http://loinc.org",
    display: Optional[str] = None,
    effective_datetime: Optional[str] = None,
) -> Observation:
    """
    Create a minimal FHIR Observation for vital signs or laboratory values.
    If you need to create a more complex observation, use the FHIR Observation resource directly.
    https://hl7.org/fhir/observation.html

    Args:
        status: REQUIRED. The status of the observation (default: "final")
        code: REQUIRED. The observation code (e.g., LOINC code for the measurement)
        value: The numeric value of the observation
        unit: The unit of measure (e.g., "beats/min", "mg/dL")
        system: The code system for the observation code (default: LOINC)
        display: The display name for the observation code
        effective_datetime: When the observation was made (ISO format). Uses current time if not provided.
        subject: Reference to the patient (e.g. "Patient/123")

    Returns:
        Observation: A FHIR Observation resource with an auto-generated ID prefixed with 'hc-'
    """
    if not effective_datetime:
        effective_datetime = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )

    subject_ref = Reference(reference=subject) if subject is not None else None

    return Observation(
        id=_generate_id(),
        status=status,
        code=create_single_codeable_concept(code, display, system),
        subject=subject_ref,
        effectiveDateTime=effective_datetime,
        valueQuantity=Quantity(
            value=value, unit=unit, system="http://unitsofmeasure.org", code=unit
        ),
    )


def create_patient(
    gender: Optional[str] = None,
    birth_date: Optional[str] = None,
    identifier: Optional[str] = None,
    identifier_system: Optional[str] = "http://hospital.example.org",
) -> Patient:
    """
    Create a minimal FHIR Patient resource with basic gender and birthdate
    If you need to create a more complex patient, use the FHIR Patient resource directly
    https://hl7.org/fhir/patient.html (No required fields).

    Args:
        gender: Administrative gender (male, female, other, unknown)
        birth_date: Birth date in YYYY-MM-DD format
        identifier: Optional identifier value for the patient (e.g., MRN)
        identifier_system: The system for the identifier (default: "http://hospital.example.org")

    Returns:
        Patient: A FHIR Patient resource with an auto-generated ID prefixed with 'hc-'
    """
    patient_data: Dict[str, Any] = {"id": _generate_id()}

    if birth_date:
        patient_data["birthDate"] = birth_date

    if gender:
        patient_data["gender"] = gender.lower()

    if identifier:
        patient_data["identifier"] = [
            Identifier(system=identifier_system, value=identifier)
        ]

    return Patient(**patient_data)


def create_risk_assessment_from_prediction(
    subject: str,
    prediction: Dict[str, Any],
    status: str = "final",
    method: Optional[CodeableConcept] = None,
    basis: Optional[List[Reference]] = None,
    comment: Optional[str] = None,
    occurrence_datetime: Optional[str] = None,
) -> RiskAssessment:
    """
    Create a FHIR RiskAssessment from ML model prediction output.
    If you need to create a more complex risk assessment, use the FHIR RiskAssessment resource directly.
    https://hl7.org/fhir/riskassessment.html

    Args:
        subject: REQUIRED. Reference to the patient (e.g. "Patient/123")
        prediction: Dictionary containing prediction details with keys:
            - outcome: CodeableConcept or dict with code, display, system for the predicted outcome
            - probability: float between 0 and 1 representing the risk probability
            - qualitative_risk: Optional str indicating risk level (e.g., "high", "moderate", "low")
        status: REQUIRED. The status of the assessment (default: "final")
        method: Optional CodeableConcept describing the assessment method/model used
        basis: Optional list of References to observations or other resources used as input
        comment: Optional text comment about the assessment
        occurrence_datetime: When the assessment was made (ISO format). Uses current time if not provided.

    Returns:
        RiskAssessment: A FHIR RiskAssessment resource with an auto-generated ID prefixed with 'hc-'

    Example:
        >>> prediction = {
        ...     "outcome": {"code": "A41.9", "display": "Sepsis", "system": "http://hl7.org/fhir/sid/icd-10"},
        ...     "probability": 0.85,
        ...     "qualitative_risk": "high"
        ... }
        >>> risk = create_risk_assessment("Patient/123", prediction)
    """
    if not occurrence_datetime:
        occurrence_datetime = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )

    outcome = prediction.get("outcome")
    if isinstance(outcome, dict):
        outcome_concept = create_single_codeable_concept(
            code=outcome["code"],
            display=outcome.get("display"),
            system=outcome.get("system", "http://snomed.info/sct"),
        )
    else:
        outcome_concept = outcome

    prediction_data: Dict[str, Any] = {"outcome": outcome_concept}

    if "probability" in prediction:
        prediction_data["probabilityDecimal"] = prediction["probability"]

    if "qualitative_risk" in prediction:
        prediction_data["qualitativeRisk"] = create_single_codeable_concept(
            code=prediction["qualitative_risk"],
            display=prediction["qualitative_risk"].capitalize(),
            system="http://terminology.hl7.org/CodeSystem/risk-probability",
        )

    risk_assessment_data: Dict[str, Any] = {
        "id": _generate_id(),
        "status": status,
        "subject": Reference(reference=subject),
        "occurrenceDateTime": occurrence_datetime,
        "prediction": [prediction_data],
    }

    if method:
        risk_assessment_data["method"] = method

    if basis:
        risk_assessment_data["basis"] = basis

    if comment:
        risk_assessment_data["note"] = [{"text": comment}]

    return RiskAssessment(**risk_assessment_data)


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
    return DocumentReference(
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

    content: Dict[str, Any] = {"attachment": attachment}

    if language:
        content["language"] = language

    content.update(kwargs)

    return content


def set_condition_category(
    condition: Condition,
    category: str,
) -> Condition:
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
    from healthchain.fhir.version import get_fhir_resource, get_resource_version

    version = get_resource_version(condition)
    CodeableConceptCls = get_fhir_resource("CodeableConcept", version)
    CodingCls = get_fhir_resource("Coding", version)

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
        CodeableConceptCls(
            coding=[
                CodingCls(
                    system="http://terminology.hl7.org/CodeSystem/condition-category",
                    code=cat_info["code"],
                    display=cat_info["display"],
                )
            ]
        )
    ]
    return condition


def create_provenance_audit_event(
   resource: Any,
   source: str,
   tag_code: Optional[str] = None,
) -> Optional[AuditEvent]:
   """
   create a FHIR AuditEvent recording that provenance metadata was added to a resource.

   Called internally by add_provenance_metadata. Records:
     - what resource was used
     - which resource system it came from
     - when it happened
     - what kind of tag code was applied (if any)
   """
   try:
       resource_type = getattr(resource, "resource_type", None) or type(resource).__name__
       resource_id = getattr(resource, "id", "unknown")

       event = AuditEvent(
           type=Coding(
               system="http://terminology.hl7.org/CodeSystem/audit-event-type",
               code="rest",
               display="RESTful Operation",
           ),
           action="U",  ## U means Update - provenance tagging modifies an existing resource
           recorded=datetime.datetime.now(datetime.timezone.utc), ## time -> when it was accessed
           outcome="0",  ## code for checking if it's success or not
           agent=[  ## who accessed it
               AuditEventAgent(
                   requestor=True,
                   who={"reference": f"Device/healthchain-gateway"},
                   network={"address": source, "type": "5"},
               )
           ],
           source=AuditEventSource(
               observer={"reference": "Device/healthchain-gateway"},
               site=source,
           ),
           entity=[ ## what is accessed
               {
                   "what": {"reference": f"{resource_type}/{resource_id}"},
                   "description": f"Provenance tagged from {source}"
                   + (f" with tag '{tag_code}'" if tag_code else ""),
               }
           ],
       )

       logger.info(
           f"PROVENANCE AUDIT: {resource_type}/{resource_id} "
           f"came from '{source}'"
           + (f" [{tag_code}]" if tag_code else "")
       )

       return event

   except Exception as e:
       logger.warning(f"Failed to create provenance audit event: {e}")


def add_provenance_metadata(
    resource: Any,
    source: str,
    tag_code: Optional[str] = None,
    tag_display: Optional[str] = None,
) -> Any:
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
    from healthchain.fhir.version import get_fhir_resource, get_resource_version

    version = get_resource_version(resource)
    MetaCls = get_fhir_resource("Meta", version)
    CodingCls = get_fhir_resource("Coding", version)

    if not resource.meta:
        resource.meta = MetaCls()

    resource.meta.source = f"urn:healthchain:source:{source}"
    resource.meta.lastUpdated = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if tag_code:
        if not resource.meta.tag:
            resource.meta.tag = []

        resource.meta.tag.append(
            CodingCls(
                system="https://dotimplement.github.io/HealthChain/fhir/tags",
                code=tag_code,
                display=tag_display or tag_code,
            )
        )

    create_provenance_audit_event(resource, source, tag_code)

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
    from healthchain.fhir.version import get_fhir_resource, get_resource_version

    version = get_resource_version(codeable_concept)
    CodingCls = get_fhir_resource("Coding", version)

    if not codeable_concept.coding:
        codeable_concept.coding = []

    codeable_concept.coding.append(CodingCls(system=system, code=code, display=display))

    return codeable_concept
