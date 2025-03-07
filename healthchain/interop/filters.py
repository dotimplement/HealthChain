from datetime import datetime
from typing import Dict, Any


def map_system(system: str, mappings: Dict) -> str:
    """Maps source code system to FHIR system"""
    if not system:
        return None
    # Access the code systems mapping directly
    return mappings.get("cda_fhir", {}).get("code_systems", {}).get(system, system)


def map_status(status: str, mappings: Dict) -> str:
    """Maps source status to FHIR status"""
    if not status:
        return None
    # Access the status mapping directly
    return mappings.get("cda_fhir", {}).get("status", {}).get(status, "unknown")


def format_date(date_str: str) -> str:
    """Formats dates to FHIR format"""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return dt.isoformat() + "Z"  # Add UTC timezone indicator
    except (ValueError, TypeError):
        return None


def clean_empty(d: Any) -> Any:
    """Recursively remove empty strings, empty lists, empty dicts, and None values"""
    if isinstance(d, dict):
        return {
            k: v
            for k, v in ((k, clean_empty(v)) for k, v in d.items())
            if v not in (None, "", {}, [])
        }
    elif isinstance(d, list):
        return [v for v in (clean_empty(v) for v in d) if v not in (None, "", {}, [])]
    return d
