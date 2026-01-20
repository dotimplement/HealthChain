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

from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING

# Keep static imports only for types that are always version-compatible
# and used in signatures/type hints
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.reference import Reference

from healthchain.fhir.elementhelpers import (
    create_single_codeable_concept,
    create_single_attachment,
)
from healthchain.fhir.utilities import _generate_id

if TYPE_CHECKING:
    from healthchain.fhir.version import FHIRVersion

logger = logging.getLogger(__name__)


def create_condition(
    subject: str,
    clinical_status: str = "active",
    code: Optional[str] = None,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
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
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.

    Returns:
        Condition: A FHIR Condition resource with an auto-generated ID prefixed with 'hc-'
    """
    from healthchain.fhir.version import get_fhir_resource

    Condition = get_fhir_resource("Condition", version)
    ReferenceClass = get_fhir_resource("Reference", version)

    if code:
        condition_code = create_single_codeable_concept(code, display, system, version)
    else:
        condition_code = None

    condition = Condition(
        id=_generate_id(),
        subject=ReferenceClass(reference=subject),
        clinicalStatus=create_single_codeable_concept(
            code=clinical_status,
            display=clinical_status.capitalize(),
            system="http://terminology.hl7.org/CodeSystem/condition-clinical",
            version=version,
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
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
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
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.

    Returns:
        MedicationStatement: A FHIR MedicationStatement resource with an auto-generated ID prefixed with 'hc-'
    """
    from healthchain.fhir.version import get_fhir_resource

    MedicationStatement = get_fhir_resource("MedicationStatement", version)
    ReferenceClass = get_fhir_resource("Reference", version)

    if code:
        medication_concept = create_single_codeable_concept(
            code, display, system, version
        )
    else:
        medication_concept = None

    medication = MedicationStatement(
        id=_generate_id(),
        subject=ReferenceClass(reference=subject),
        status=status,
        medication={"concept": medication_concept},
    )

    return medication


def create_allergy_intolerance(
    patient: str,
    code: Optional[str] = None,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
    """
    Create a minimal active FHIR AllergyIntolerance.
    If you need to create a more complex allergy intolerance, use the FHIR AllergyIntolerance resource directly.
    https://build.fhir.org/allergyintolerance.html

    Args:
        patient: REQUIRED. Reference to the patient (e.g. "Patient/123")
        code: The allergen code
        display: The display name for the allergen
        system: The code system (default: SNOMED CT)
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.

    Returns:
        AllergyIntolerance: A FHIR AllergyIntolerance resource with an auto-generated ID prefixed with 'hc-'
    """
    from healthchain.fhir.version import get_fhir_resource

    AllergyIntolerance = get_fhir_resource("AllergyIntolerance", version)
    ReferenceClass = get_fhir_resource("Reference", version)

    if code:
        allergy_code = create_single_codeable_concept(code, display, system, version)
    else:
        allergy_code = None

    allergy = AllergyIntolerance(
        id=_generate_id(),
        patient=ReferenceClass(reference=patient),
        code=allergy_code,
    )

    return allergy


def create_value_quantity_observation(
    code: str,
    value: float,
    unit: str,
    status: str = "final",
    subject: Optional[str] = None,
    system: str = "http://loinc.org",
    display: Optional[str] = None,
    effective_datetime: Optional[str] = None,
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
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
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.

    Returns:
        Observation: A FHIR Observation resource with an auto-generated ID prefixed with 'hc-'
    """
    from healthchain.fhir.version import get_fhir_resource

    Observation = get_fhir_resource("Observation", version)
    ReferenceClass = get_fhir_resource("Reference", version)
    Quantity = get_fhir_resource("Quantity", version)

    if not effective_datetime:
        effective_datetime = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )
    subject_ref = None
    if subject is not None:
        subject_ref = ReferenceClass(reference=subject)

    observation = Observation(
        id=_generate_id(),
        status=status,
        code=create_single_codeable_concept(code, display, system, version),
        subject=subject_ref,
        effectiveDateTime=effective_datetime,
        valueQuantity=Quantity(
            value=value, unit=unit, system="http://unitsofmeasure.org", code=unit
        ),
    )

    return observation


def create_patient(
    gender: Optional[str] = None,
    birth_date: Optional[str] = None,
    identifier: Optional[str] = None,
    identifier_system: Optional[str] = "http://hospital.example.org",
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
    """
    Create a minimal FHIR Patient resource with basic gender and birthdate
    If you need to create a more complex patient, use the FHIR Patient resource directly
    https://hl7.org/fhir/patient.html (No required fields).

    Args:
        gender: Administrative gender (male, female, other, unknown)
        birth_date: Birth date in YYYY-MM-DD format
        identifier: Optional identifier value for the patient (e.g., MRN)
        identifier_system: The system for the identifier (default: "http://hospital.example.org")
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.

    Returns:
        Patient: A FHIR Patient resource with an auto-generated ID prefixed with 'hc-'
    """
    from healthchain.fhir.version import get_fhir_resource

    Patient = get_fhir_resource("Patient", version)
    Identifier = get_fhir_resource("Identifier", version)

    patient_id = _generate_id()

    patient_data: Dict[str, Any] = {"id": patient_id}

    if birth_date:
        patient_data["birthDate"] = birth_date

    if gender:
        patient_data["gender"] = gender.lower()

    if identifier:
        patient_data["identifier"] = [
            Identifier(
                system=identifier_system,
                value=identifier,
            )
        ]

    patient = Patient(**patient_data)
    return patient


def create_risk_assessment_from_prediction(
    subject: str,
    prediction: Dict[str, Any],
    status: str = "final",
    method: Optional[CodeableConcept] = None,
    basis: Optional[List[Reference]] = None,
    comment: Optional[str] = None,
    occurrence_datetime: Optional[str] = None,
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
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
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.

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
    from healthchain.fhir.version import get_fhir_resource

    RiskAssessment = get_fhir_resource("RiskAssessment", version)
    ReferenceClass = get_fhir_resource("Reference", version)

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
            version=version,
        )
    else:
        outcome_concept = outcome

    prediction_data: Dict[str, Any] = {
        "outcome": outcome_concept,
    }

    if "probability" in prediction:
        prediction_data["probabilityDecimal"] = prediction["probability"]

    if "qualitative_risk" in prediction:
        prediction_data["qualitativeRisk"] = create_single_codeable_concept(
            code=prediction["qualitative_risk"],
            display=prediction["qualitative_risk"].capitalize(),
            system="http://terminology.hl7.org/CodeSystem/risk-probability",
            version=version,
        )

    risk_assessment_data: Dict[str, Any] = {
        "id": _generate_id(),
        "status": status,
        "subject": ReferenceClass(reference=subject),
        "occurrenceDateTime": occurrence_datetime,
        "prediction": [prediction_data],
    }

    if method:
        risk_assessment_data["method"] = method

    if basis:
        risk_assessment_data["basis"] = basis

    if comment:
        risk_assessment_data["note"] = [{"text": comment}]

    risk_assessment = RiskAssessment(**risk_assessment_data)

    return risk_assessment


def create_document_reference(
    data: Optional[Any] = None,
    url: Optional[str] = None,
    content_type: Optional[str] = None,
    status: str = "current",
    description: Optional[str] = "DocumentReference created by HealthChain",
    attachment_title: Optional[str] = "Attachment created by HealthChain",
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
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
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.

    Returns:
        DocumentReference: A FHIR DocumentReference resource with an auto-generated ID prefixed with 'hc-'
    """
    from healthchain.fhir.version import get_fhir_resource

    DocumentReference = get_fhir_resource("DocumentReference", version)

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
                    version=version,
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
    version: Optional[Union["FHIRVersion", str]] = None,
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
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.
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
        version=version,
    )

    content: Dict[str, Any] = {
        "attachment": attachment,
    }

    if language:
        content["language"] = language

    content.update(kwargs)

    return content


def set_condition_category(
    condition: Any,
    category: str,
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
    """
    Set the category of a FHIR Condition to either 'problem-list-item' or 'encounter-diagnosis'.

    Args:
        condition: The FHIR Condition resource to modify
        category: The category to set. Must be 'problem-list-item' or 'encounter-diagnosis'.
        version: FHIR version to use. If None, attempts to detect from the condition resource.

    Returns:
        Condition: The modified FHIR Condition resource with the specified category set

    Raises:
        ValueError: If the category is not one of the allowed values.
    """
    from healthchain.fhir.version import get_resource_version

    # Detect version from resource if not provided
    if version is None:
        version = get_resource_version(condition)

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
            version=version,
        )
    ]
    return condition


def add_provenance_metadata(
    resource: Any,
    source: str,
    tag_code: Optional[str] = None,
    tag_display: Optional[str] = None,
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
    """Add provenance metadata to a FHIR resource.

    Adds source system identifier, timestamp, and optional processing tags to track
    data lineage and transformations for audit trails.

    Args:
        resource: The FHIR resource to annotate
        source: Name of the source system (e.g., "epic", "cerner")
        tag_code: Optional tag code for processing operations (e.g., "aggregated", "deduplicated")
        tag_display: Optional display text for the tag
        version: FHIR version to use. If None, attempts to detect from the resource.

    Returns:
        Resource: The resource with added provenance metadata

    Example:
        >>> condition = create_condition(subject="Patient/123", code="E11.9")
        >>> condition = add_provenance_metadata(condition, "epic", "aggregated", "Aggregated from source")
    """
    from healthchain.fhir.version import get_fhir_resource, get_resource_version

    # Detect version from resource if not provided
    if version is None:
        version = get_resource_version(resource)

    Meta = get_fhir_resource("Meta", version)
    Coding = get_fhir_resource("Coding", version)

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
    codeable_concept: Any,
    code: str,
    system: str,
    display: Optional[str] = None,
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
    """Add a coding to an existing CodeableConcept.

    Useful for adding standardized codes (e.g., SNOMED CT) to resources that already
    have codes from other systems (e.g., ICD-10).

    Args:
        codeable_concept: The CodeableConcept to add coding to
        code: The code value from the code system
        system: The code system URI
        display: Optional display text for the code
        version: FHIR version to use. If None, attempts to detect from the CodeableConcept.

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

    # Detect version from CodeableConcept if not provided
    if version is None:
        version = get_resource_version(codeable_concept)

    Coding = get_fhir_resource("Coding", version)

    if not codeable_concept.coding:
        codeable_concept.coding = []

    codeable_concept.coding.append(Coding(system=system, code=code, display=display))

    return codeable_concept
