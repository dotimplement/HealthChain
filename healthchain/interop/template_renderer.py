"""
Template Renderer for HealthChain Interoperability Engine

This module provides a base class for template rendering functionality.
"""

import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path

from healthchain.interop.filters import clean_empty

log = logging.getLogger(__name__)


class TemplateRenderer:
    """Base class for template rendering functionality"""

    def __init__(self, config_manager, template_registry):
        """Initialize the template renderer

        Args:
            config_manager: Configuration manager instance
            template_registry: Template registry instance
        """
        self.config_manager = config_manager
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
        template_path = self.config_manager.get_config_value(
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
            log.error(f"Failed to render template: {str(e)}")
            return None

    def get_section_config(self, section_key: str) -> Dict:
        """Get configuration for a specific section

        Args:
            section_key: Key identifying the section

        Returns:
            Section configuration dictionary
        """
        return self.config_manager.get_config_value(f"sections.{section_key}", {})

    def get_section_configs(self) -> Dict:
        """Get configurations for all sections

        Returns:
            Dictionary of section configurations
        """
        return self.config_manager.get_section_configs()
