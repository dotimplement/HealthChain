from typing import Optional, Dict, Any

# Common system URIs
SNOMED_CT_URI = "http://snomed.info/sct"
ICD10_URI = "http://hl7.org/fhir/sid/icd-10"
LOINC_URI = "http://loinc.org"


def create_coding(
    code: str,
    system: str,
    display: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a standardized FHIR Coding dict.

    Mirrors the FHIR Coding structure and keeps optional fields omitted when None,
    which matches how other helpers in the codebase behave.
    """
    coding: Dict[str, Any] = {
        "system": system,
        "code": code,
    }
    if display is not None:
        coding["display"] = display
    if version is not None:
        coding["version"] = version
    return coding


