"""FHIR utility functions.

This module provides utility functions for common operations like ID generation,
age calculation, and gender encoding.
"""

import datetime
import uuid
from typing import Optional


def _generate_id() -> str:
    """Generate a unique ID prefixed with 'hc-'.

    Returns:
        str: A unique ID string prefixed with 'hc-'
    """
    return f"hc-{str(uuid.uuid4())}"


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
