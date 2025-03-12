import logging
from pathlib import Path
from typing import Dict, Callable, Optional

from liquid import Environment, FileSystemLoader

log = logging.getLogger(__name__)


class TemplateRegistry:
    """Manages loading and accessing Liquid templates for the InteropEngine"""

    def __init__(self, template_dir: Path):
        """Initialize the TemplateRegistry

        Args:
            template_dir: Directory containing template files
        """
        self.template_dir = template_dir
        self._templates = {}
        self._env = None
        self._filters = {}

        if not template_dir.exists():
            raise ValueError(f"Template directory not found: {template_dir}")

    def initialize(self, filters: Dict[str, Callable] = None) -> "TemplateRegistry":
        """Initialize the Liquid environment and load templates

        Args:
            filters: Dictionary of filter names to filter functions

        Returns:
            Self for method chaining
        """
        # Store initial filters
        if filters:
            self._filters.update(filters)

        self._create_environment()
        self._load_templates()
        return self

    def _create_environment(self) -> None:
        """Create and configure the Liquid environment with registered filters"""
        self._env = Environment(loader=FileSystemLoader(str(self.template_dir)))

        # Register all filters
        for name, func in self._filters.items():
            self._env.filters[name] = func

    def add_filter(self, name: str, filter_func: Callable) -> "TemplateRegistry":
        """Add a custom filter function

        Args:
            name: Name of the filter to use in templates
            filter_func: Filter function to register

        Returns:
            Self for method chaining
        """
        # Add to internal filter registry
        self._filters[name] = filter_func

        # If environment is already initialized, register the filter
        if self._env:
            self._env.filters[name] = filter_func

        return self

    def add_filters(self, filters: Dict[str, Callable]) -> "TemplateRegistry":
        """Add multiple custom filter functions

        Args:
            filters: Dictionary of filter names to filter functions

        Returns:
            Self for method chaining
        """
        for name, func in filters.items():
            self.add_filter(name, func)

        return self

    def get_filter(self, name: str) -> Optional[Callable]:
        """Get a registered filter function by name

        Args:
            name: Name of the filter

        Returns:
            The filter function or None if not found
        """
        return self._filters.get(name)

    def get_filters(self) -> Dict[str, Callable]:
        """Get all registered filter functions

        Returns:
            Dictionary of filter names to filter functions
        """
        return self._filters.copy()

    def _load_templates(self) -> None:
        """Load all template files"""
        if not self._env:
            raise ValueError("Environment not initialized. Call initialize() first.")

        # Walk through all subdirectories to find template files
        for template_file in self.template_dir.rglob("*.liquid"):
            rel_path = template_file.relative_to(self.template_dir)
            template_key = rel_path.stem

            try:
                template = self._env.get_template(str(rel_path))
                self._templates[template_key] = template
                log.debug(f"Loaded template: {template_key}")
            except Exception as e:
                log.error(f"Failed to load template {template_file}: {str(e)}")
                continue

        if not self._templates:
            raise ValueError(f"No templates found in {self.template_dir}")

        log.info(f"Loaded {len(self._templates)} templates")

    def get_template(self, template_key: str):
        """Get a template by key

        Args:
            template_key: Template identifier

        Returns:
            The template object

        Raises:
            KeyError: If template not found
        """
        if template_key not in self._templates:
            raise KeyError(f"Template not found: {template_key}")

        return self._templates[template_key]

    def has_template(self, template_key: str) -> bool:
        """Check if a template exists

        Args:
            template_key: Template identifier

        Returns:
            True if template exists, False otherwise
        """
        return template_key in self._templates

    def get_all_templates(self) -> Dict:
        """Get all templates

        Returns:
            Dict of template keys to template objects
        """
        return self._templates
