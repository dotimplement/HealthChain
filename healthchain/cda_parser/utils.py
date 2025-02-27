import yaml
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum

log = logging.getLogger(__name__)


class MappingStrategy(Enum):
    """Defines how to handle multiple matches when converting FHIR to CDA."""

    FIRST = "first"  # Return first match found
    ALL = "all"  # Return all matches as list
    ERROR = "error"  # Raise error if multiple matches found


# TODO: Dates, times, human readable names, etc.
class CodeMapping:
    """Handles bidirectional mapping between CDA and FHIR codes and formats."""

    # Default mappings as fallback
    DEFAULT_MAPPINGS = {
        "system": {
            "cda_to_fhir": {
                "2.16.840.1.113883.6.96": "http://snomed.info/sct",
                "2.16.840.1.113883.3.26.1.1": "http://ncit.nci.nih.gov",
                "2.16.840.1.113883.6.88": "http://www.nlm.nih.gov/research/umls/rxnorm",
            }
        },
        "status": {
            "cda_to_fhir": {
                "active": "active",
                "completed": "resolved",
                "aborted": "inactive",
                "suspended": "inactive",
            }
        },
        "date_format": {
            "cda_to_fhir": {
                "YYYYMMDD": "YYYY-MM-DD",
            }
        },
        "severity": {
            "cda_to_fhir": {
                "H": "severe",
                "M": "moderate",
                "L": "mild",
            }
        },
    }

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize with optional config file path."""
        self.mappings = self._load_mappings(config_path)
        self._validate_mappings()

    def _load_mappings(self, config_path: Optional[Union[str, Path]] = None) -> Dict:
        """Load mappings from config file if provided, else use defaults."""
        if not config_path:
            return self.DEFAULT_MAPPINGS

        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            log.error(f"Failed to load mappings from {config_path}: {e}")
            log.warning("Falling back to default mappings")
            return self.DEFAULT_MAPPINGS

    def _validate_mappings(self) -> None:
        """Validate mapping structure and log warnings for potential issues."""
        for mapping_type, mapping_data in self.mappings.items():
            if "cda_to_fhir" not in mapping_data:
                log.warning(f"Missing cda_to_fhir mapping for {mapping_type}")

            # Check for duplicate FHIR codes
            fhir_codes = {}
            for cda, fhir in mapping_data.get("cda_to_fhir", {}).items():
                if fhir in fhir_codes:
                    log.warning(
                        f"Duplicate FHIR mapping found in {mapping_type}: "
                        f"{fhir} maps to both {cda} and {fhir_codes[fhir]}"
                    )
                fhir_codes[fhir] = cda

    def cda_to_fhir(
        self,
        code: str,
        mapping_type: str,
        case_sensitive: bool = False,
        default: Any = None,
    ) -> Optional[str]:
        """Convert CDA code to FHIR code."""
        try:
            mapping = self.mappings[mapping_type]["cda_to_fhir"]

            # Add null check for code
            if code is None:
                log.error(f"Received None code for mapping type '{mapping_type}'")
                return default

            if not case_sensitive:
                code = code.lower()
                mapping = {k.lower(): v for k, v in mapping.items()}

            result = mapping.get(code, default)
            if result is None:
                log.debug(f"No mapping found for CDA code '{code}' in {mapping_type}")
            return result

        except KeyError:
            log.error(f"Invalid mapping type: {mapping_type}")
            return default
        except AttributeError as e:
            log.error(f"Invalid code type for '{code}' in {mapping_type}: {str(e)}")
            return default
        except Exception as e:
            log.error(
                f"Unexpected error converting code '{code}' in {mapping_type}: {str(e)}"
            )
            return default

    def fhir_to_cda(
        self,
        code: str,
        mapping_type: str,
        strategy: MappingStrategy = MappingStrategy.FIRST,
        case_sensitive: bool = False,
        default: Any = None,
    ) -> Union[str, List[str], None]:
        """Convert FHIR code to CDA code(s)."""
        try:
            mapping = self.mappings[mapping_type]["cda_to_fhir"]
            if not case_sensitive:
                code = code.lower()
                mapping = {k: v.lower() for k, v in mapping.items()}

            matches = [cda for cda, fhir in mapping.items() if fhir == code]

            if not matches:
                log.debug(f"No mapping found for FHIR code '{code}' in {mapping_type}")
                return default

            if len(matches) > 1:
                if strategy == MappingStrategy.ERROR:
                    raise ValueError(
                        f"Multiple CDA codes found for FHIR code '{code}': {matches}"
                    )
                elif strategy == MappingStrategy.ALL:
                    return matches

            return matches[0]

        except KeyError:
            log.error(f"Invalid mapping type: {mapping_type}")
            return default

    def get_mapping_types(self) -> List[str]:
        """Return list of available mapping types."""
        return list(self.mappings.keys())

    def add_mapping(self, mapping_type: str, cda_code: str, fhir_code: str) -> None:
        """Add a new mapping pair."""
        if mapping_type not in self.mappings:
            self.mappings[mapping_type] = {"cda_to_fhir": {}}

        self.mappings[mapping_type]["cda_to_fhir"][cda_code] = fhir_code
        log.info(f"Added mapping: {mapping_type} - {cda_code} -> {fhir_code}")

    # TODO: use datetime
    @classmethod
    def convert_date_cda_to_fhir(cls, date_str: Optional[str]) -> Optional[str]:
        """Convert CDA date format (YYYYMMDD) to FHIR date format (YYYY-MM-DD).

        Args:
            date_str: Date string in CDA format (YYYYMMDD)

        Returns:
            Date string in FHIR format (YYYY-MM-DD) or None if input is invalid
        """
        if not date_str or not isinstance(date_str, str):
            return None

        # Validate input format
        if not date_str.isdigit() or len(date_str) != 8:
            log.warning(f"Invalid CDA date format: {date_str}")
            return None

        try:
            from datetime import datetime

            parsed_date = datetime.strptime(date_str, "%Y%m%d")
            return parsed_date.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            log.warning(f"Invalid CDA date format: {date_str}")
            return None

    @classmethod
    def convert_date_fhir_to_cda(cls, date_str: Optional[str]) -> Optional[str]:
        """Convert FHIR date format (YYYY-MM-DD) to CDA date format (YYYYMMDD).

        Args:
            date_str: Date string in FHIR format (YYYY-MM-DD)

        Returns:
            Date string in CDA format (YYYYMMDD) or None if input is invalid
        """
        if not date_str or not isinstance(date_str, str):
            return None

        # Validate input format
        if not len(date_str) == 10 or date_str[4] != "-" or date_str[7] != "-":
            log.warning(f"Invalid FHIR date format: {date_str}")
            return None

        try:
            from datetime import datetime

            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            return parsed_date.strftime("%Y%m%d")
        except (ValueError, TypeError):
            log.warning(f"Invalid FHIR date format: {date_str}")
            return None
