import yaml
import json
import uuid
import logging
import importlib
import re
import xmltodict

from enum import Enum
from typing import Dict, List, Union
from pathlib import Path
from datetime import datetime

from liquid import Environment, FileSystemLoader
from fhir.resources.resource import Resource
from fhir.resources.bundle import Bundle

from .parsers.cda import CDAParser
from .filters import format_date, clean_empty

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
        """Register custom filters with Liquid environment"""

        # Create filter functions with access to mappings
        def map_system_filter(system, direction="fhir_to_cda"):
            """Map between CDA and FHIR code systems

            Args:
                system: The system URI/OID to map
                direction: Either 'fhir_to_cda' or 'cda_to_fhir'
            """
            if not system:
                return None

            shared_mappings = self.mappings.get("shared_mappings", {})
            system_mappings = shared_mappings.get("code_systems", {}).get(direction, {})
            return system_mappings.get(system, system)

        def map_status_filter(status, direction="fhir_to_cda"):
            """Map between CDA and FHIR status codes

            Args:
                status: The status code to map
                direction: Either 'fhir_to_cda' or 'cda_to_fhir'
            """
            if not status:
                return None

            shared_mappings = self.mappings.get("shared_mappings", {})
            status_mappings = shared_mappings.get("status_codes", {}).get(direction, {})
            return status_mappings.get(status, status)

        def json_filter(obj):
            if obj is None:
                return "[]"
            return json.dumps(obj)

        def generate_id_filter(value=None):
            """Generate UUID or use provided value"""
            return value if value else f"hc-{str(uuid.uuid4())}"

        def format_timestamp_filter(value=None):
            """Format timestamp or use current time"""
            if value:
                return value.strftime("%Y%m%d%H%M%S")
            return datetime.now().strftime("%Y%m%d%H%M%S")

        # Register filters with descriptive names
        self.env.filters["map_system"] = map_system_filter
        self.env.filters["map_status"] = map_status_filter
        self.env.filters["format_date"] = format_date
        self.env.filters["json"] = json_filter
        self.env.filters["generate_id"] = generate_id_filter
        self.env.filters["format_timestamp"] = format_timestamp_filter

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
        """Convert CDA XML to FHIR resources

        Args:
            source_data: CDA document as XML string

        Returns:
            List[Resource]: List of FHIR resources

        Raises:
            ValueError: If required mappings are missing or if sections are unsupported
        """
        resources = []

        # Get required configurations
        cda_fhir_config = self.mappings.get("cda_fhir", {})
        section_mappings = cda_fhir_config.get("sections", {})
        if not section_mappings:
            raise ValueError("No section mappings found in cda_fhir.yaml")

        # Parse sections from CDA XML
        section_entries = {}
        for section_key, section_config in section_mappings.items():
            try:
                entries = self.parser.parse_section(source_data, section_config)
                if entries:
                    section_entries[section_key] = entries
            except Exception as e:
                log.error(f"Failed to parse section {section_key}: {str(e)}")
                continue

        # Convert entries to FHIR resources
        for section_key, entries in section_entries.items():
            section_config = section_mappings[section_key]
            template_key = Path(section_config["template"]).stem

            if template_key not in self.templates:
                log.warning(
                    f"Template {template_key} not found, skipping section {section_key}"
                )
                continue

            template = self.templates[template_key]

            # Convert each entry using template
            for entry in entries:
                try:
                    # Render template with entry data
                    rendered = template.render(
                        {"entry": entry, "section_config": section_config}
                    )

                    # Parse rendered JSON and clean empty values
                    resource_dict = clean_empty(json.loads(rendered))

                    # Add required fields based on resource type
                    resource_type = section_config["resource"]
                    self._add_required_fields(resource_dict, resource_type)

                    # Create FHIR resource instance
                    try:
                        resource_module = importlib.import_module(
                            f"fhir.resources.{resource_type.lower()}"
                        )
                        resource_class = getattr(resource_module, resource_type)
                        resource = resource_class(**resource_dict)
                        resources.append(resource)
                    except Exception as e:
                        log.error(f"Failed to create FHIR resource: {str(e)}")
                        continue

                except Exception as e:
                    log.error(
                        f"Failed to convert entry in section {section_key}: {str(e)}"
                    )
                    continue

        return resources

    def _add_required_fields(self, resource_dict: Dict, resource_type: str):
        """Add required fields to resource dictionary based on type"""
        # Add common fields
        if "id" not in resource_dict:
            resource_dict["id"] = f"hc-{str(uuid.uuid4())}"
        if "subject" not in resource_dict:
            resource_dict["subject"] = {"reference": "Patient/example"}

        # Add resource-specific required fields
        if resource_type == "Condition":
            if "clinicalStatus" not in resource_dict:
                resource_dict["clinicalStatus"] = {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "unknown",
                        }
                    ]
                }
        elif resource_type == "MedicationStatement":
            if "status" not in resource_dict:
                resource_dict["status"] = "unknown"
        elif resource_type == "AllergyIntolerance":
            if "clinicalStatus" not in resource_dict:
                resource_dict["clinicalStatus"] = {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                            "code": "unknown",
                        }
                    ]
                }

    def _hl7v2_to_fhir(self, source_data: str) -> List[Resource]:
        """Convert HL7v2 to FHIR resources"""
        raise NotImplementedError("HL7v2 to FHIR conversion not implemented")

    def _fhir_to_cda(self, resources: Union[Resource, List[Resource]]) -> str:
        """Convert FHIR resources to CDA XML

        Args:
            resources: A FHIR Bundle, list of resources, or single resource

        Returns:
            str: CDA document as XML string

        Raises:
            ValueError: If required mappings are missing or if resource types are unsupported
        """
        # Normalize input to list of resources
        resource_list = []
        if isinstance(resources, Bundle):
            resource_list.extend(
                entry.resource for entry in resources.entry if entry.resource
            )
        elif isinstance(resources, list):
            resource_list = resources
        else:
            resource_list = [resources]

        # Get required configurations
        sections_config = self.mappings.get("fhir_cda", {}).get("sections", {})
        document_config = self.mappings.get("fhir_cda", {}).get("document", {})

        if not sections_config or not document_config:
            raise ValueError("No section or document mappings found in fhir_cda.yaml")

        # Group resources by section
        section_entries = {}
        for resource in resource_list:
            resource_type = resource.__class__.__name__

            # Find matching section for resource type
            section_key = next(
                (
                    key
                    for key, config in sections_config.items()
                    if config["resource"] == resource_type
                ),
                None,
            )

            if not section_key:
                log.warning(f"Unsupported resource type: {resource_type}")
                continue

            # Render Entries
            template_name = Path(sections_config[section_key]["template"]).stem
            if template_name not in self.templates:
                log.warning(
                    f"Template {template_name} not found, skipping section {section_key}"
                )
                continue

            try:
                timestamp = datetime.now().strftime(format="%Y%m%d")
                reference_name = "#" + str(uuid.uuid4())[:8] + "name"
                context = {
                    "timestamp": timestamp,
                    "text_reference_name": reference_name,
                }
                entry_json = self.templates[template_name].render(
                    resource=resource.model_dump(), context=context
                )
                entry = clean_empty(json.loads(entry_json))

                section_entries.setdefault(section_key, []).append(entry)
            except Exception as e:
                log.error(f"Failed to render {section_key} entry: {str(e)}")
                continue

        # Render sections
        formatted_sections = []
        section_template = self.templates["cda_section"]
        for section_key, section_config in sections_config.items():
            if section_entries.get(section_key):
                try:
                    section_json = section_template.render(
                        config=section_config, entries=section_entries[section_key]
                    )
                    formatted_sections.append(json.loads(section_json))
                except Exception as e:
                    log.error(f"Failed to render section {section_key}: {str(e)}")
                    continue

        # Create document context
        context = {
            "bundle": resources if isinstance(resources, Bundle) else None,
            "document": document_config,
            "formatted_sections": formatted_sections,
        }

        # Render document
        document_json = self.templates["cda_document"].render(**context)
        document_dict = json.loads(document_json)
        xml_string = xmltodict.unparse(document_dict, pretty=True)

        # Fix self-closing tags
        return re.sub(r"(<(\w+)(\s+[^>]*?)?)></\2>", r"\1/>", xml_string)

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
