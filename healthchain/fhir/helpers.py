"""Convenience functions for creating minimal FHIR resources.
Patterns:
- create_*(): create a new FHIR resource with sensible defaults - useful for dev, use with caution
- add_*(): add data to resources with list fields safely (e.g. coding)
- set_*(): set the field of specific resources with soft validation (e.g. category)
- read_*(): return a human readable format of the data in a resource (e.g. attachments)

Parameters marked REQUIRED are required by FHIR specification.
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
from fhir.resources.observation import Observation
from fhir.resources.riskassessment import RiskAssessment
from fhir.resources.patient import Patient
from fhir.resources.quantity import Quantity
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.attachment import Attachment
from fhir.resources.resource import Resource
from fhir.resources.reference import Reference
from fhir.resources.meta import Meta
from fhir.resources.identifier import Identifier


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
    subject_ref = None
    if subject is not None:
        subject_ref = Reference(reference=subject)

    observation = Observation(
        id=_generate_id(),
        status=status,
        code=create_single_codeable_concept(code, display, system),
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
    patient_id = _generate_id()

    patient_data = {"id": patient_id}

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

    prediction_data = {
        "outcome": outcome_concept,
    }

    if "probability" in prediction:
        prediction_data["probabilityDecimal"] = prediction["probability"]

    if "qualitative_risk" in prediction:
        prediction_data["qualitativeRisk"] = create_single_codeable_concept(
            code=prediction["qualitative_risk"],
            display=prediction["qualitative_risk"].capitalize(),
            system="http://terminology.hl7.org/CodeSystem/risk-probability",
        )

    risk_assessment_data = {
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

    risk_assessment = RiskAssessment(**risk_assessment_data)

    return risk_assessment


# TODO: create a function that creates a DocumentReferenceContent to add to the DocumentReference
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


def calculate_age_from_birthdate(birth_date: str) -> Optional[int]:
    """Calculate age in years from a birth date string.

    Args:
        birth_date: Birth date in ISO format (YYYY-MM-DD or full ISO datetime)

    Returns:
        Age in years, or None if birth date is invalid
    """
    if not birth_date:
        return None

    try:
        if isinstance(birth_date, str):
            # Remove timezone info for simpler parsing
            birth_date_clean = birth_date.replace("Z", "").split("T")[0]
            birth_dt = datetime.datetime.strptime(birth_date_clean, "%Y-%m-%d")
        else:
            birth_dt = birth_date

        # Calculate age
        today = datetime.datetime.now()
        age = today.year - birth_dt.year

        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (birth_dt.month, birth_dt.day):
            age -= 1

        return age
    except (ValueError, AttributeError, TypeError):
        return None


def calculate_age_from_event_date(birth_date: str, event_date: str) -> Optional[int]:
    """Calculate age in years from birth date and event date (MIMIC-IV style).

    Uses the formula: age = year(eventDate) - year(birthDate)
    This matches MIMIC-IV on FHIR de-identified age calculation.

    Args:
        birth_date: Birth date in ISO format (YYYY-MM-DD or full ISO datetime)
        event_date: Event date in ISO format (YYYY-MM-DD or full ISO datetime)

    Returns:
        Age in years based on year difference, or None if dates are invalid

    Example:
        >>> calculate_age_from_event_date("1990-06-15", "2020-03-10")
        30
    """
    if not birth_date or not event_date:
        return None

    try:
        # Parse birth date
        if isinstance(birth_date, str):
            birth_date_clean = birth_date.replace("Z", "").split("T")[0]
            birth_year = int(birth_date_clean.split("-")[0])
        else:
            birth_year = birth_date.year

        # Parse event date
        if isinstance(event_date, str):
            event_date_clean = event_date.replace("Z", "").split("T")[0]
            event_year = int(event_date_clean.split("-")[0])
        else:
            event_year = event_date.year

        # MIMIC-IV style: simple year difference
        age = event_year - birth_year

        return age
    except (ValueError, AttributeError, TypeError, IndexError):
        return None


def encode_gender(gender: str) -> Optional[int]:
    """Encode gender as integer for ML models.

    Standard encoding: Male=1, Female=0, Other/Unknown=None

    Args:
        gender: Gender string (case-insensitive)

    Returns:
        Encoded gender (1 for male, 0 for female, None for other/unknown)
    """
    if not gender:
        return None

    gender_lower = gender.lower()
    if gender_lower in ["male", "m"]:
        return 1
    elif gender_lower in ["female", "f"]:
        return 0
    else:
        return None
