import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union


def map_system(
    system: str, mappings: Dict = None, direction: str = "fhir_to_cda"
) -> Optional[str]:
    """Maps between CDA and FHIR code systems

    Args:
        system: The code system to map
        mappings: Mappings dictionary (if None, returns system unchanged)
        direction: Direction of mapping ('fhir_to_cda' or 'cda_to_fhir')

    Returns:
        Mapped code system or original if no mapping found
    """
    if not system:
        return None

    if not mappings:
        return system

    shared_mappings = mappings.get("shared_mappings", {})
    system_mappings = shared_mappings.get("code_systems", {}).get(direction, {})
    return system_mappings.get(system, system)


def map_status(
    status: str, mappings: Dict = None, direction: str = "fhir_to_cda"
) -> Optional[str]:
    """Maps between CDA and FHIR status codes

    Args:
        status: The status code to map
        mappings: Mappings dictionary (if None, returns status unchanged)
        direction: Direction of mapping ('fhir_to_cda' or 'cda_to_fhir')

    Returns:
        Mapped status code or original if no mapping found
    """
    if not status:
        return None

    if not mappings:
        return status

    shared_mappings = mappings.get("shared_mappings", {})
    status_mappings = shared_mappings.get("status_codes", {}).get(direction, {})
    return status_mappings.get(status, status)


def map_severity(
    severity_code: str, mappings: Dict = None, direction: str = "cda_to_fhir"
) -> Optional[str]:
    """Maps between CDA and FHIR severity codes

    Args:
        severity_code: The severity code to map
        mappings: Mappings dictionary (if None, returns severity code unchanged)
        direction: Direction of mapping ('cda_to_fhir' or 'fhir_to_cda')

    Returns:
        Mapped severity code or original if no mapping found
    """
    if not severity_code:
        return None

    if not mappings:
        return severity_code

    shared_mappings = mappings.get("shared_mappings", {})
    severity_mappings = shared_mappings.get("severity_codes", {}).get(direction, {})
    return severity_mappings.get(severity_code, severity_code)


# TODO: Make this date formatter more complete
def format_date(
    date_str: str, input_format: str = "%Y%m%d", output_format: str = "iso"
) -> Optional[str]:
    """Formats dates to the specified format

    Args:
        date_str: Date string to format
        input_format: Input date format (default: "%Y%m%d")
        output_format: Output format - "iso" for ISO format or a strftime format string

    Returns:
        Formatted date string or None if formatting fails
    """
    if not date_str:
        return None

    try:
        dt = datetime.strptime(date_str, input_format)
        if output_format == "iso":
            return dt.isoformat() + "Z"  # Add UTC timezone indicator
        else:
            return dt.strftime(output_format)
    except (ValueError, TypeError):
        return None


def format_timestamp(value=None, format_str: str = "%Y%m%d%H%M%S") -> str:
    """Format timestamp or use current time

    Args:
        value: Datetime object to format (if None, uses current time)
        format_str: Format string for strftime

    Returns:
        Formatted timestamp string
    """
    if value:
        return value.strftime(format_str)
    return datetime.now().strftime(format_str)


def generate_id(value=None, prefix: str = "hc-") -> str:
    """Generate UUID or use provided value

    Args:
        value: Existing ID to use (if None, generates a new UUID)
        prefix: Prefix to add to generated UUID

    Returns:
        ID string
    """
    return value if value else f"{prefix}{str(uuid.uuid4())}"


def to_json(obj: Any) -> str:
    """Convert object to JSON string

    Args:
        obj: Object to convert to JSON

    Returns:
        JSON string representation
    """
    if obj is None:
        return "[]"
    return json.dumps(obj)


def extract_effective_period(
    effective_times: Union[Dict, List[Dict], None],
) -> Optional[Dict]:
    """Extract effective period data from CDA effectiveTime elements

    Processes CDA effectiveTime elements of type IVL_TS to extract start/end dates
    for a FHIR effectivePeriod.

    Args:
        effective_times: Single effectiveTime element or list of effectiveTime elements

    Returns:
        Dictionary with 'start' and/or 'end' fields, or None if no period found
    """
    if not effective_times:
        return None

    # Ensure we have a list to work with
    if not isinstance(effective_times, list):
        effective_times = [effective_times]

    # Look for IVL_TS type effective times
    for effective_time in effective_times:
        if effective_time.get("@xsi:type") == "IVL_TS":
            result = {}

            # Extract low value (start date)
            low_value = effective_time.get("low", {}).get("@value")
            if low_value:
                result["start"] = format_date(low_value)

            # Extract high value (end date)
            high_value = effective_time.get("high", {}).get("@value")
            if high_value:
                result["end"] = format_date(high_value)

            # Return the period if we found start or end date
            if result:
                return result

    # No period found
    return None


def extract_effective_timing(
    effective_times: Union[Dict, List[Dict], None],
) -> Optional[Dict]:
    """Extract timing data from CDA effectiveTime elements

    Processes CDA effectiveTime elements of type PIVL_TS to extract frequency/timing
    for FHIR dosage.timing.

    Args:
        effective_times: Single effectiveTime element or list of effectiveTime elements

    Returns:
        Dictionary with 'period' and 'periodUnit' fields, or None if no timing found
    """
    if not effective_times:
        return None

    # Ensure we have a list to work with
    if not isinstance(effective_times, list):
        effective_times = [effective_times]

    # Look for PIVL_TS type effective times with period
    for effective_time in effective_times:
        if effective_time.get("@xsi:type") == "PIVL_TS" and effective_time.get(
            "period"
        ):
            period = effective_time.get("period")
            if period and "@value" in period and "@unit" in period:
                return {
                    "period": float(period.get("@value")),
                    "periodUnit": period.get("@unit"),
                }

    # No timing information found
    return None


def clean_empty(d: Any) -> Any:
    """Recursively remove empty strings, empty lists, empty dicts, and None values

    Args:
        d: Data structure to clean

    Returns:
        Cleaned data structure
    """
    if isinstance(d, dict):
        return {
            k: v
            for k, v in ((k, clean_empty(v)) for k, v in d.items())
            if v not in (None, "", {}, [])
        }
    elif isinstance(d, list):
        return [v for v in (clean_empty(v) for v in d) if v not in (None, "", {}, [])]
    return d


def _ensure_list(value: Any) -> List:
    """Convert a value to a list if it isn't already one"""
    if not isinstance(value, list):
        return [value]
    return value


def _get_template_ids(section: Dict) -> List[Dict]:
    """Get template IDs from a section, ensuring they are in list form"""
    if not section.get("templateId"):
        return []
    return _ensure_list(section["templateId"])


def _get_entry_relationships(observation: Dict) -> List[Dict]:
    """Get entry relationships from an observation, ensuring they are in list form"""
    relationships = observation.get("entryRelationship")
    if not relationships:
        return []
    return _ensure_list(relationships)


def extract_clinical_status(observation: Dict, config: Dict) -> Optional[str]:
    """Extract clinical status from a CDA allergy entry.
    Not sure how to do this in liquid, so doing it here for now.

    Args:
        observation: CDA observation containing allergy information
        config: Config dictionary

    Returns:
        Clinical status code or None if not found
    """
    if not observation or not isinstance(observation, dict):
        return None

    # Look for clinical status in entry relationships
    for rel in _get_entry_relationships(observation):
        if not rel.get("observation", {}).get("templateId"):
            continue

        # Check each template ID
        for template in _get_template_ids(rel["observation"]):
            if template.get("@root") == config.get("template", {}).get(
                "clinical_status_obs", {}
            ).get("template_id"):
                if rel.get("observation", {}).get("value", {}).get("@code"):
                    return rel["observation"]["value"]["@code"]

    return None


def extract_reactions(observation: Dict, config: Dict) -> List[Dict]:
    """Extract reaction information from a CDA allergy entry

    Args:
        observation: CDA observation containing allergy information
        config: Config dictionary

    Returns:
        List of reaction dictionaries, each with system, code, display, and severity
    """
    if not observation or not isinstance(observation, dict):
        return []

    reactions = []

    # Process each entry relationship
    for rel in _get_entry_relationships(observation):
        if not rel.get("observation", {}).get("templateId"):
            continue

        # Look for reaction template ID
        for template in _get_template_ids(rel["observation"]):
            if template.get("@root") == config.get("identifiers", {}).get(
                "reaction", {}
            ).get("template_id"):
                # Found a reaction observation
                reaction = {}

                # Extract manifestation
                if rel.get("observation", {}).get("value"):
                    value = rel["observation"]["value"]
                    reaction = {
                        "system": value.get("@codeSystem"),
                        "code": value.get("@code"),
                        "display": value.get("@displayName"),
                        "severity": None,
                    }

                    # Check for severity in nested entry relationship
                    for sev in _get_entry_relationships(rel["observation"]):
                        # Ensure observation and templateId exist
                        if not sev.get("observation", {}).get("templateId"):
                            continue

                        # Look for severity template ID
                        for sev_template in _get_template_ids(sev["observation"]):
                            if sev_template.get("@root") == config.get(
                                "identifiers", {}
                            ).get("severity", {}).get("template_id"):
                                if (
                                    sev.get("observation", {})
                                    .get("value", {})
                                    .get("@code")
                                ):
                                    reaction["severity"] = sev["observation"]["value"][
                                        "@code"
                                    ]
                                    break

                if "system" in reaction and "code" in reaction:
                    reactions.append(reaction)
                break

    return reactions
