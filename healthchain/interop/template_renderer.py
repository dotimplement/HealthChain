"""
Template Renderer for HealthChain Interoperability Engine

This module provides a base class for template rendering functionality.
"""

import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path

from liquid import Template

from healthchain.config.base import ConfigManager
from healthchain.interop.template_registry import TemplateRegistry
from healthchain.interop.filters import clean_empty

log = logging.getLogger(__name__)


class TemplateRenderer:
    """Base class for template rendering functionality.

    This class provides core template rendering capabilities using Liquid templates.
    It works with a ConfigManager to look up template configurations and a
    TemplateRegistry to store and retrieve templates.

    The renderer supports:
    - Loading templates by name from the registry
    - Looking up templates based on section configurations
    - Rendering templates with context data
    - Cleaning empty values from rendered output
    - JSON parsing of rendered templates

    Attributes:
        config (ConfigManager): Configuration manager instance for looking up template paths
        template_registry (TemplateRegistry): Registry storing available templates
    """

    def __init__(self, config: ConfigManager, template_registry: TemplateRegistry):
        """Initialize the template renderer

        Args:
            config: Configuration manager instance
            template_registry: Template registry instance
        """
        self.config = config
        self.template_registry = template_registry

    def get_template(self, template_name: str) -> Optional[Template]:
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

    def get_template_from_section_config(
        self, section_key: str, template_type: str
    ) -> Optional[Template]:
        """Get the template for a given section and template type from configuration.

        Looks up the template path from configuration using section_key and template_type,
        extracts the template name (stem) from the path, and retrieves the template from
        the registry if it exists.

        Args:
            section_key: Key identifying the section (e.g. 'problems', 'medications')
            template_type: Type of template to look up (e.g. 'resource', 'entry', 'section')

        Returns:
            Template instance if found and valid, None if template name not in config
            or template not found in registry

        Example:
            >>> renderer.get_template_from_section_config('problems', 'entry')
            <Template 'problem_entry'>
        """
        # Get template path from configuration
        template_path = self.config.get_config_value(
            f"sections.{section_key}.{template_type}_template"
        )
        if not template_path:
            log.warning(
                f"No {template_type} template specified for section: {section_key}"
            )
            return None

        # Extract template name (stem) from path
        template_name = Path(template_path).stem

        # Check if template exists in registry
        if not self.template_registry.has_template(template_name):
            log.warning(
                f"Template '{template_name}' not found for section {section_key}"
            )
            return None

        # Get template from registry
        return self.template_registry.get_template(template_name)

    def render_template(self, template, context: Dict[str, Any]) -> Optional[Dict]:
        """Render a template with the given context and return parsed JSON result.

        Renders the template using the provided context, parses the rendered output as JSON,
        and cleans any empty values from the resulting dictionary.

        Args:
            template: The Liquid template object to render
            context: Dictionary containing variables and data to use in template rendering

        Returns:
            Dict: The rendered template output parsed as JSON with empty values removed
            None: If template rendering or JSON parsing fails

        Example:
            >>> context = {"patient": {"name": "John Doe"}}
            >>> result = renderer.render_template(template, context)
            >>> print(result)
            {'patient': {'name': 'John Doe'}}
        """
        try:
            rendered = template.render(context)
            return clean_empty(json.loads(rendered))
        except Exception as e:
            log.error(f"Failed to render template {template.name}: {str(e)}")
            return None
