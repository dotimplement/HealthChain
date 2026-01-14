"""FHIR element creation functions.

This module provides convenience functions for creating FHIR elements that are used
as building blocks within FHIR resources (e.g., CodeableConcept, Attachment, Coding).
"""

import logging
import base64
import datetime

from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from healthchain.fhir.version import FHIRVersion

logger = logging.getLogger(__name__)


def create_single_codeable_concept(
    code: str,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
    """
    Create a minimal FHIR CodeableConcept with a single coding.

    Args:
        code: REQUIRED. The code value from the code system
        display: The display name for the code
        system: The code system (default: SNOMED CT)
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.

    Returns:
        CodeableConcept: A FHIR CodeableConcept resource with a single coding
    """
    from healthchain.fhir.version import get_fhir_resource

    CodeableConcept = get_fhir_resource("CodeableConcept", version)
    Coding = get_fhir_resource("Coding", version)

    return CodeableConcept(coding=[Coding(system=system, code=code, display=display)])


def create_single_reaction(
    code: str,
    display: Optional[str] = None,
    system: Optional[str] = "http://snomed.info/sct",
    severity: Optional[str] = None,
    version: Optional[Union["FHIRVersion", str]] = None,
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
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.

    Returns:
        A list containing a single FHIR Reaction dictionary with manifestation and severity fields
    """
    from healthchain.fhir.version import get_fhir_resource

    CodeableConcept = get_fhir_resource("CodeableConcept", version)
    CodeableReference = get_fhir_resource("CodeableReference", version)
    Coding = get_fhir_resource("Coding", version)

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
    version: Optional[Union["FHIRVersion", str]] = None,
) -> Any:
    """Create a minimal FHIR Attachment.

    Creates a FHIR Attachment resource with basic fields. Either data or url should be provided.
    If data is provided, it will be base64 encoded.

    Args:
        content_type: The MIME type of the content
        data: The actual data content to be base64 encoded
        url: The URL where the data can be found
        title: A title for the attachment (default: "Attachment created by HealthChain")
        version: FHIR version to use (e.g., "R4B", "STU3"). Defaults to current default.

    Returns:
        Attachment: A FHIR Attachment resource with basic metadata and content
    """
    from healthchain.fhir.version import get_fhir_resource

    Attachment = get_fhir_resource("Attachment", version)

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
