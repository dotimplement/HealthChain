import logging
from pathlib import Path
from typing import Dict, Callable

from liquid import Environment, FileSystemLoader, Template

log = logging.getLogger(__name__)


class TemplateRegistry:
    """Manages loading and accessing Liquid templates for the InteropEngine.

    The TemplateRegistry handles loading Liquid template files from a directory and making them
    available for rendering. It supports custom filter functions that can be used within templates.

    Key features:
    - Loads .liquid template files recursively from a directory
    - Supports adding custom filter functions
    - Provides template lookup by name
    - Validates template existence

    Example:
        registry = TemplateRegistry(Path("templates"))
        registry.initialize({
            "uppercase": str.upper,
            "lowercase": str.lower
        })
        template = registry.get_template("cda_fhir/condition")
    """

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
        """Initialize the Liquid environment and load templates.

        This method sets up the Liquid template environment by:
        1. Storing any provided filter functions
        2. Creating the Liquid environment with the template directory
        3. Loading all template files from the directory

        The environment must be initialized before templates can be loaded or rendered.

        Args:
            filters: Optional dictionary mapping filter names to filter functions that can be used
                    in templates. For example: {"uppercase": str.upper}

        Returns:
            TemplateRegistry: Returns self for method chaining

        Raises:
            ValueError: If template directory does not exist or environment initialization fails
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

    def _load_templates(self) -> None:
        """Load all Liquid template files from the template directory.

        This method recursively walks through the template directory and its subdirectories
        to find all .liquid template files. Each template is loaded into the environment
        and stored in the internal template registry using its full relative path (without extension)
        as the key (e.g., "cda_fhir/document"). This is not required but recommended for clarity.
        """
        if not self._env:
            raise ValueError("Environment not initialized. Call initialize() first.")

        # Walk through all subdirectories to find template files
        for template_file in self.template_dir.rglob("*.liquid"):
            rel_path = template_file.relative_to(self.template_dir)
            # Use full path without extension as the key (e.g., "cda_fhir/document")
            template_key = str(rel_path.with_suffix(""))

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

    def get_template(self, template_key: str) -> Template:
        """Get a template by key

        Args:
            template_key: Template identifier. Can be a full path (e.g., 'cda_fhir/document')
                or just a filename (e.g., 'document').

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
            template_key: Template identifier. Can be a full path (e.g., 'cda_fhir/document')
                or just a filename (e.g., 'document').

        Returns:
            True if template exists, False otherwise
        """
        return template_key in self._templates
