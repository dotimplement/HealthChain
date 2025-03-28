"""
Template Renderer for HealthChain Interoperability Engine

This module provides a base class for template rendering functionality.
"""

import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path

from healthchain.config.base import ConfigManager
from healthchain.interop.template_registry import TemplateRegistry
from healthchain.interop.filters import clean_empty

log = logging.getLogger(__name__)


class TemplateRenderer:
    """Base class for template rendering functionality"""

    def __init__(self, config: ConfigManager, template_registry: TemplateRegistry):
        """Initialize the template renderer

        Args:
            config: Configuration manager instance
            template_registry: Template registry instance
        """
        self.config = config
        self.template_registry = template_registry

    def get_template(self, template_name: str):
        """Get a template by name

        Args:
            template_name: Name of the template to retrieve

        Returns:
            The template instance or None if not found
        """
        try:
            return self.template_registry.get_template(template_name)
        except KeyError:
            log.warning(f"Template '{template_name}' not found")
            return None

    def get_section_template_name(
        self, section_key: str, template_type: str
    ) -> Optional[str]:
        """Get the template name for a given section and template type

        Args:
            section_key: Key identifying the section
            template_type: Type of template (e.g., 'resource', 'entry')

        Returns:
            Template name or None if not found
        """
        template_path = self.config.get_config_value(
            f"sections.{section_key}.{template_type}_template", ""
        )

        if not template_path:
            log.warning(
                f"No {template_type} template specified for section: {section_key}"
            )
            return None

        return Path(template_path).stem

    def get_section_template(self, section_key: str, template_type: str):
        """Get the template for a given section and template type

        Args:
            section_key: Key identifying the section
            template_type: Type of template (e.g., 'resource', 'entry')

        Returns:
            Template instance or None if not found
        """
        template_name = self.get_section_template_name(section_key, template_type)

        if not template_name:
            return None

        if not self.template_registry.has_template(template_name):
            log.warning(
                f"Template '{template_name}' not found for section {section_key}"
            )
            return None

        return self.template_registry.get_template(template_name)

    def render_template(self, template, context: Dict[str, Any]) -> Optional[Dict]:
        """Render a template with the given context

        Args:
            template: The template to render
            context: Context dictionary for rendering

        Returns:
            Rendered dictionary or None if rendering failed
        """
        try:
            rendered = template.render(context)
            return clean_empty(json.loads(rendered))
        except Exception as e:
            log.error(f"Failed to render template {template.name}: {str(e)}")
            return None

    def get_validated_section_config(self, section_key: str) -> Dict:
        """Get a validated section configuration

        Args:
            section_key: Key identifying the section

        Returns:
            A validated section configuration

        Raises:
            ValueError: If the section configuration doesn't exist or is invalid
        """
        validated_sections = self.config.get_section_configs(validate=True)
        if section_key not in validated_sections:
            # Check if the section exists at all (might have failed validation)
            all_sections = self.config.get_section_configs(validate=False)
            if section_key not in all_sections:
                raise ValueError(f"Section configuration not found: {section_key}")
            else:
                raise ValueError(f"Section configuration is invalid: {section_key}")

        return validated_sections[section_key]
