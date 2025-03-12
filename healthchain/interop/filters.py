import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional


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
