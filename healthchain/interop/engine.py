import yaml
import json
import uuid
import logging
import importlib

from enum import Enum
from typing import Dict, List, Union
from pathlib import Path

from liquid import Environment, FileSystemLoader
from fhir.resources.resource import Resource

from .parsers.cda import CDAParser
from .filters import map_system, map_status, format_date, clean_empty

log = logging.getLogger(__name__)


class FormatType(Enum):
    HL7V2 = "hl7v2"
    CDA = "cda"
    FHIR = "fhir"


def validate_format(format_type: Union[str, FormatType]) -> FormatType:
    if isinstance(format_type, str):
        try:
            return FormatType[format_type.upper()]
        except KeyError:
            raise ValueError(f"Unsupported format: {format_type}")
    else:
        return format_type


class InteropEngine:
    """Generic interoperability engine for converting between healthcare formats"""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.mappings = self._load_mappings()

        # Create Liquid environment with loader and custom filters
        template_dir = self.config_dir / "templates"
        if not template_dir.exists():
            raise ValueError(f"Template directory not found: {template_dir}")

        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self._register_filters()

        self.templates = self._load_templates()
        self.parser = CDAParser(self.mappings)

    def _register_filters(self):
        # TODO: Can be more configurable
        """Register custom filters with Liquid environment"""

        # Create filter functions with access to mappings
        def map_system_filter(system):
            return map_system(system, self.mappings)

        def map_status_filter(status):
            return map_status(status, self.mappings)

        # Register filters with descriptive names
        self.env.filters["map_system"] = map_system_filter
        self.env.filters["map_status"] = map_status_filter
        self.env.filters["format_date"] = format_date

    def _load_mappings(self) -> Dict:
        """Load all mapping configurations"""
        mappings = {}
        mapping_dir = self.config_dir / "mappings"
        for mapping_file in mapping_dir.glob("*.yaml"):
            with open(mapping_file) as f:
                mappings[mapping_file.stem] = yaml.safe_load(f)

        return mappings

    def _load_templates(self) -> Dict:
        """Load all liquid templates"""
        templates = {}

        # Walk through all subdirectories to find template files
        for template_file in (self.config_dir / "templates").rglob("*.liquid"):
            rel_path = template_file.relative_to(self.config_dir / "templates")
            template_key = rel_path.stem

            try:
                template = self.env.get_template(str(rel_path))
                templates[template_key] = template

            except Exception as e:
                log.error(f"Failed to load template {template_file}: {str(e)}")
                continue

        if not templates:
            raise ValueError(f"No templates found in {self.config_dir / 'templates'}")

        log.debug(f"Loaded {len(templates)} templates: {list(templates.keys())}")

        return templates

    def _cda_to_fhir(self, source_data: str) -> List[Resource]:
        """Convert CDA XML to FHIR resources"""
        resources = []

        # Get problems section config
        # TODO: read sections from config
        section_config = self.mappings["cda_fhir"]["sections"]["problems"]
        template_key = section_config["template"].replace(".liquid", "").split("/")[-1]

        log.debug(f"Using template key: {template_key}")
        template = self.templates[template_key]

        # TODO: maybe parse patient reference from source data and preserve header info
        entries = self.parser.parse_section(source_data, section_config)

        # Convert each entry using template
        for entry in entries:
            try:
                # Render template with entry data
                rendered = template.render(
                    {"entry": entry, "section_config": section_config}
                )

                # Parse rendered JSON to dict and clean empty values
                resource_dict = clean_empty(json.loads(rendered))

                # Add required fields
                if "id" not in resource_dict:
                    resource_dict["id"] = "hc-" + str(uuid.uuid4())
                if "subject" not in resource_dict:
                    resource_dict["subject"] = {"reference": "Patient/foo"}
                if "clinicalStatus" not in resource_dict:
                    resource_dict["clinicalStatus"] = {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                "code": "unknown",
                            }
                        ]
                    }

                # Get the FHIR resource class dynamically
                try:
                    resource_type = resource_dict["resourceType"]
                    resource_module = importlib.import_module(
                        f"fhir.resources.{resource_type.lower()}"
                    )
                    resource_class = getattr(resource_module, resource_type)

                    # Create resource instance
                    resource = resource_class(**resource_dict)
                    resources.append(resource)
                except Exception as e:
                    log.error(f"Failed to create FHIR resource: {str(e)}")
                    continue

            except Exception as e:
                log.error(f"Failed to convert entry: {str(e)}")
                continue

        return resources

    def _hl7v2_to_fhir(self, source_data: str) -> List[Resource]:
        """Convert HL7v2 to FHIR resources"""
        raise NotImplementedError("HL7v2 to FHIR conversion not implemented")

    def _fhir_to_cda(self, resources: List[Resource]) -> str:
        """Convert FHIR resources to CDA"""
        raise NotImplementedError("FHIR to CDA conversion not implemented")

    def _fhir_to_hl7v2(self, resources: List[Resource]) -> str:
        """Convert FHIR resources to HL7v2"""
        raise NotImplementedError("FHIR to HL7v2 conversion not implemented")

    def to_fhir(
        self, source_data: str, source_format: Union[str, FormatType]
    ) -> List[Resource]:
        """Convert source format to FHIR resources"""
        format_type = validate_format(source_format)

        if format_type == FormatType.CDA:
            return self._cda_to_fhir(source_data)
        elif format_type == FormatType.HL7V2:
            return self._hl7v2_to_fhir(source_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def from_fhir(
        self,
        resources: List[Resource],
        format_type: Union[str, FormatType],
    ) -> str:
        """Convert FHIR resources to HL7v2 or CDA"""
        format_type = validate_format(format_type)

        if format_type == FormatType.HL7V2:
            return self._fhir_to_hl7v2(resources)
        elif format_type == FormatType.CDA:
            return self._fhir_to_cda(resources)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
