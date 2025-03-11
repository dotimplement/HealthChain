import yaml
import json
import uuid
import logging
import importlib
import re
import xmltodict

from enum import Enum
from typing import Dict, List, Union, Optional
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
        self.mappings = self._load_configs("mappings")
        self.configs = self._load_configs("configs")

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

    def _load_configs(self, directory: str) -> Dict:
        """Load all configuration files"""
        configs = {}
        config_dir = self.config_dir / directory
        for config_file in config_dir.rglob("*.yaml"):
            with open(config_file) as f:
                configs[config_file.stem] = yaml.safe_load(f)

        return configs

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
        # Get required configurations
        section_configs = self.configs.get("section", {})

        if not section_configs:
            raise ValueError("No section configs found in configs/cda/section.yaml")

        # Parse sections from CDA XML
        section_entries = self._parse_cda_sections(source_data, section_configs)

        # Convert entries to FHIR resources
        return self._convert_entries_to_fhir(section_entries, section_configs)

    def _parse_cda_sections(self, source_data: str, section_configs: Dict) -> Dict:
        """Parse sections from CDA XML document

        Args:
            source_data: CDA document as XML string
            section_configs: Configuration for each section

        Returns:
            Dict: Dictionary mapping section keys to their entries
        """
        section_entries = {}

        for section_key, section_config in section_configs.items():
            try:
                entries = self.parser.parse_section(source_data, section_config)
                if entries:
                    section_entries[section_key] = entries
            except Exception as e:
                log.error(f"Failed to parse section {section_key}: {str(e)}")
                continue

        return section_entries

    def _convert_entries_to_fhir(
        self, section_entries: Dict, section_configs: Dict
    ) -> List[Resource]:
        """Convert parsed CDA entries to FHIR resources

        Args:
            section_entries: Dictionary mapping section keys to their entries
            section_configs: Configuration for each section

        Returns:
            List[Resource]: List of FHIR resources
        """
        resources = []

        for section_key, entries in section_entries.items():
            section_config = section_configs[section_key]
            template_key = Path(section_config["resource_template"]).stem

            if template_key not in self.templates:
                log.warning(
                    f"Template {template_key} not found, skipping section {section_key}"
                )
                continue

            template = self.templates[template_key]

            # Process each entry in the section
            section_resources = self._process_section_entries(
                entries, template, section_config, section_key
            )
            resources.extend(section_resources)

        return resources

    def _process_section_entries(
        self, entries: List[Dict], template, section_config: Dict, section_key: str
    ) -> List[Resource]:
        """Process entries from a single section and convert to FHIR resources

        Args:
            entries: List of entries from a section
            template: The template to use for rendering
            section_config: Configuration for the section
            section_key: Key identifying the section

        Returns:
            List[Resource]: List of FHIR resources from this section
        """
        resources = []
        resource_type = section_config["resource"]

        for entry in entries:
            try:
                # Convert entry to FHIR resource dictionary
                resource_dict = self._render_and_process_entry(
                    entry, template, section_config
                )

                # Create FHIR resource instance
                resource = self._create_fhir_resource(resource_dict, resource_type)
                if resource:
                    resources.append(resource)

            except Exception as e:
                log.error(f"Failed to convert entry in section {section_key}: {str(e)}")
                continue

        return resources

    def _render_and_process_entry(
        self, entry: Dict, template, section_config: Dict
    ) -> Dict:
        """Render an entry using a template and process the result

        Args:
            entry: The entry data
            template: The template to use for rendering
            section_config: Configuration for the section

        Returns:
            Dict: Processed resource dictionary
        """
        # Render template with entry data and config
        rendered = template.render({"entry": entry, "config": section_config})

        # Parse rendered JSON and clean empty values
        resource_dict = clean_empty(json.loads(rendered))

        # Add required fields based on resource type
        resource_type = section_config["resource"]
        self._add_required_fields(resource_dict, resource_type)

        return resource_dict

    def _create_fhir_resource(
        self, resource_dict: Dict, resource_type: str
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
            log.error(f"Failed to create FHIR resource: {str(e)}")
            return None

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
        resource_list = self._normalize_resources(resources)

        # Get required configurations
        section_configs = self.configs.get("section", {})
        document_config = self.configs.get("document", {})

        if not section_configs or not document_config:
            raise ValueError("No section or document configs found in configs/cda")

        # Process resources and generate section entries
        section_entries = self._process_resources_to_section_entries(
            resource_list, section_configs
        )

        # Render sections
        formatted_sections = self._render_sections(section_entries, section_configs)

        # Generate final CDA document
        return self._generate_cda_document(
            resources, document_config, formatted_sections
        )

    def _normalize_resources(
        self, resources: Union[Resource, List[Resource]]
    ) -> List[Resource]:
        """Convert input resources to a normalized list format"""
        if isinstance(resources, Bundle):
            return [entry.resource for entry in resources.entry if entry.resource]
        elif isinstance(resources, list):
            return resources
        else:
            return [resources]

    def _process_resources_to_section_entries(
        self, resources: List[Resource], section_configs: Dict
    ) -> Dict:
        """Process resources and group them by section with rendered entries"""
        section_entries = {}

        for resource in resources:
            resource_type = resource.__class__.__name__

            # Find matching section for resource type
            section_key = next(
                (
                    key
                    for key, config in section_configs.items()
                    if config["resource"] == resource_type
                ),
                None,
            )

            if not section_key:
                log.warning(f"Unsupported resource type: {resource_type}")
                continue

            # Get template for this section
            template_name = Path(section_configs[section_key]["entry_template"]).stem
            if template_name not in self.templates:
                log.warning(
                    f"Template {template_name} not found, skipping section {section_key}"
                )
                continue

            # Render entry using template
            entry = self._render_entry(
                resource, section_key, template_name, section_configs[section_key]
            )
            if entry:
                section_entries.setdefault(section_key, []).append(entry)

        return section_entries

    def _render_entry(
        self,
        resource: Resource,
        section_key: str,
        template_name: str,
        section_config: Dict,
    ) -> Dict:
        """Render a single entry for a resource"""
        try:
            # Create context with common values
            timestamp = datetime.now().strftime(format="%Y%m%d")
            reference_name = "#" + str(uuid.uuid4())[:8] + "name"
            context = {
                "timestamp": timestamp,
                "text_reference_name": reference_name,
            }

            # Render template
            entry_json = self.templates[template_name].render(
                resource=resource.model_dump(),
                config=section_config,
                context=context,
            )

            # Parse and clean the rendered JSON
            return clean_empty(json.loads(entry_json))

        except Exception as e:
            log.error(f"Failed to render {section_key} entry: {str(e)}")
            return None

    def _render_sections(
        self, section_entries: Dict, section_configs: Dict
    ) -> List[Dict]:
        """Render all sections with their entries"""
        formatted_sections = []
        section_template = self.templates["cda_section"]

        for section_key, section_config in section_configs.items():
            entries = section_entries.get(section_key, [])
            if not entries:
                continue

            try:
                section_json = section_template.render(
                    entries=entries,
                    config=section_config,
                )
                formatted_sections.append(json.loads(section_json))
            except Exception as e:
                log.error(f"Failed to render section {section_key}: {str(e)}")

        return formatted_sections

    def _generate_cda_document(
        self,
        resources: Union[Resource, List[Resource]],
        document_config: Dict,
        formatted_sections: List[Dict],
    ) -> str:
        """Generate the final CDA document"""
        # Create document context
        context = {
            "bundle": resources if isinstance(resources, Bundle) else None,
            "config": document_config,
            "sections": formatted_sections,
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
