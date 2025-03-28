import yaml
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

log = logging.getLogger(__name__)


def _deep_merge(target: Dict, source: Dict) -> None:
    """Deep merge source dictionary into target dictionary

    Args:
        target: Target dictionary to merge into
        source: Source dictionary to merge from
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            # If both are dictionaries, recursively merge
            _deep_merge(target[key], value)
        else:
            # Otherwise, overwrite the value
            target[key] = value


def _get_nested_value(data: Dict, parts: List[str]) -> Any:
    """Get a nested value from a dictionary using a list of keys

    Args:
        data: Dictionary to search in
        parts: List of keys representing the path

    Returns:
        The value if found, None otherwise
    """
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current


def _load_yaml_files_recursively(directory: Path, skip_files: set = None) -> Dict:
    """Load YAML files recursively from a directory with nested structure

    Args:
        directory: Directory to load files from
        skip_files: Optional set of filenames to skip

    Returns:
        Dict of loaded configurations with nested structure
    """
    configs = {}
    skip_files = skip_files or set()

    for config_file in directory.rglob("*.yaml"):
        if config_file.name in skip_files:
            continue

        try:
            with open(config_file) as f:
                # Get relative path from directory for hierarchical keys
                rel_path = config_file.relative_to(directory)
                parent_dirs = list(rel_path.parent.parts)

                # Load the YAML content
                content = yaml.safe_load(f)

                # If the file is in a subdirectory, create nested structure
                if parent_dirs and parent_dirs[0] != ".":
                    # Start with the file's stem as the deepest key
                    current_level = {config_file.stem: content}

                    # Work backwards through parent directories to build nested dict
                    for parent in reversed(parent_dirs):
                        current_level = {parent: current_level}

                    # Merge with existing configs
                    _deep_merge(configs, current_level)
                else:
                    # Top-level file, just use the stem as key
                    configs[config_file.stem] = content

            log.debug(f"Loaded configuration file: {config_file}")
        except Exception as e:
            log.error(f"Failed to load configuration file {config_file}: {str(e)}")

    return configs


class ValidationLevel:
    """Validation levels for configuration"""

    STRICT = "strict"  # Raise exceptions for missing or invalid config
    WARN = "warn"  # Log warnings but continue
    IGNORE = "ignore"  # Skip validation entirely


class ConfigManager:
    """Manages loading and accessing configuration files for the HealthChain project"""

    def __init__(
        self,
        config_dir: Path,
        validation_level: str = ValidationLevel.STRICT,
        module: Optional[str] = None,
    ):
        """Initialize the ConfigManager

        Args:
            config_dir: Base directory containing configuration files
            validation_level: Level of validation to perform
            module: Optional module name to load specific configs for
        """
        self.config_dir = config_dir
        self._module = module
        self._validation_level = validation_level
        self._defaults = {}
        self._env_configs = {}
        self._module_configs = {}
        self._mappings = {}
        self._loaded = False
        self._environment = self._detect_environment()

    def _detect_environment(self) -> str:
        """Detect the current environment from environment variables

        Returns:
            String representing the environment (development, testing, production)
        """
        # Check for environment variable
        env = os.environ.get("HEALTHCHAIN_ENV", "development").lower()

        # Validate environment
        valid_envs = ["development", "testing", "production"]
        if env not in valid_envs:
            log.warning(f"Invalid environment '{env}', defaulting to 'development'")
            env = "development"

        log.info(f"Detected environment: {env}")
        return env

    def load(self, environment: Optional[str] = None) -> "ConfigManager":
        """Load configuration files in priority order: defaults, environment, module

        This method loads configuration files in the following order:
        1. defaults.yaml - Base configuration defaults
        2. environments/{env}.yaml - Environment-specific configuration
        3. {module}/*.yaml - Module-specific configuration files (if module specified)

        After loading, validates the configuration unless validation is ignored.

        Args:
            environment: Optional environment name to override detected environment

        Returns:
            Self for method chaining

        Raises:
            ValidationError: If validation fails and validation_level is STRICT
        """
        if environment:
            self._environment = environment

        self._load_defaults()
        self._load_environment_config()

        if self._module:
            self._load_module_configs(self._module)

        self._loaded = True

        if self._validation_level != ValidationLevel.IGNORE:
            self.validate()

        return self

    def _load_defaults(self) -> None:
        """Load the defaults.yaml file if it exists"""
        defaults_file = self.config_dir / "defaults.yaml"
        if defaults_file.exists():
            try:
                with open(defaults_file) as f:
                    self._defaults = yaml.safe_load(f)
                log.debug(f"Loaded defaults from {defaults_file}")
            except Exception as e:
                log.error(f"Failed to load defaults file {defaults_file}: {str(e)}")
                self._defaults = {}
        else:
            log.warning(f"Defaults file not found: {defaults_file}")
            self._defaults = {}

    def _load_environment_config(self) -> None:
        """Load environment-specific configuration file"""
        env_file = self.config_dir / "environments" / f"{self._environment}.yaml"
        if env_file.exists():
            try:
                with open(env_file) as f:
                    self._env_configs = yaml.safe_load(f)
                log.debug(f"Loaded environment configuration from {env_file}")
            except Exception as e:
                log.error(f"Failed to load environment file {env_file}: {str(e)}")
                self._env_configs = {}
        else:
            log.warning(f"Environment file not found: {env_file}")
            self._env_configs = {}

    def _load_module_configs(self, module: str) -> None:
        """Load module-specific configurations

        Args:
            module: Module name to load configs for
        """
        module_dir = self.config_dir / module

        if not module_dir.exists() or not module_dir.is_dir():
            log.warning(f"Module config directory not found: {module_dir}")
            self._module_configs[module] = {}
            return

        self._module_configs[module] = _load_yaml_files_recursively(module_dir)
        log.debug(
            f"Loaded {len(self._module_configs[module])} configurations for module {module}: {self._module_configs[module]}"
        )

    def _load_mappings(self) -> Dict:
        """Load mappings from the mapping directory

        Returns:
            Dict of mappings
        """
        if not self._mappings:
            mappings_dir = self.config_dir / "mappings"

            if not mappings_dir.exists():
                log.warning(f"Mappings directory not found: {mappings_dir}")
                self._mappings = {}
                return self._mappings

            # Load each YAML file in the mappings directory
            for config_file in mappings_dir.rglob("*.yaml"):
                try:
                    with open(config_file) as f:
                        self._mappings[config_file.stem] = yaml.safe_load(f)
                    log.debug(f"Loaded mapping file: {config_file}")
                except Exception as e:
                    log.error(f"Failed to load mapping file {config_file}: {str(e)}")

        return self._mappings

    def _find_config_section(
        self, module_name: str, section_name: str, subsection: Optional[str] = None
    ) -> Dict:
        """Find a configuration section in the module configs,
        searching first at top-level then in subdirectories.

        Args:
            module_name: Name of the module to search in (e.g. "interop")
            section_name: Name of the section to find (e.g. "sections", "document")
            subsection: Optional subsection key to look for within the section

        Returns:
            Configuration dict or empty dict if not found. If subsection is specified,
            returns that subsection's config or empty dict if not found.
        """
        # Look directly in module configs
        if section_name in self._module_configs[module_name]:
            section = self._module_configs[module_name][section_name]
            if isinstance(section, dict):
                if subsection:
                    return section.get(subsection, {})
                return section

        # Look in subdirectories
        for value in self._module_configs[module_name].values():
            if isinstance(value, dict) and section_name in value:
                if isinstance(value[section_name], dict):
                    if subsection:
                        return value[section_name].get(subsection, {})
                    return value[section_name]

        if subsection:
            log.warning(f"No {section_name} config found for: {subsection}")

        return {}

    def get_mappings(self) -> Dict:
        """Get all mappings, loading them first if needed

        Returns:
            Dict of mappings
        """
        return self._load_mappings()

    def get_defaults(self) -> Dict:
        """Get all default values

        Returns:
            Dict of default values
        """
        if not self._loaded:
            self.load()
        return self._defaults

    def get_environment_configs(self) -> Dict:
        """Get environment-specific configuration

        Returns:
            Dict of environment-specific configuration
        """
        if not self._loaded:
            self.load()
        return self._env_configs

    def get_environment(self) -> str:
        """Get the current environment

        Returns:
            String representing the current environment
        """
        return self._environment

    def set_environment(self, environment: str) -> "ConfigManager":
        """Set the environment and reload environment-specific configuration

        Args:
            environment: Environment to set (development, testing, production)

        Returns:
            Self for method chaining
        """
        self._environment = environment
        self._load_environment_config()
        return self

    def get_configs(self) -> Dict:
        """Get all configuration values merged according to precedence order.

        This method merges configuration values from different sources in a simplified
        three-layer precedence order:

        1. Module-specific configs (highest priority, if a module is specified)
        2. Environment-specific configs (middle priority)
        3. Default configs (lowest priority)

        The configurations are deep merged, meaning nested dictionary values are
        recursively combined rather than overwritten.

        Returns:
            Dict: A merged dictionary containing all configuration values according
                 to the precedence order.
        """
        if not self._loaded:
            self.load()

        merged_configs = {}

        # Start with defaults (lowest priority)
        _deep_merge(merged_configs, self._defaults)

        # Apply environment-specific configs (middle priority)
        _deep_merge(merged_configs, self._env_configs)

        # Apply module-specific configs if a module is specified (highest priority)
        if self._module and self._module in self._module_configs:
            _deep_merge(merged_configs, self._module_configs[self._module])

        return merged_configs

    def get_config_value(self, path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation path

        Args:
            path: Dot notation path
            default: Default value if path not found

        Returns:
            Configuration value or default
        """
        if not self._loaded:
            self.load()

        # Split the path into parts
        parts = path.split(".")

        # Create merged configs with proper precedence
        configs = self.get_configs()

        # Get the value from merged configs
        value = _get_nested_value(configs, parts)
        if value is not None:
            return value

        # Return the provided default if not found
        return default

    def validate(self) -> bool:
        """Validate that all required configurations are present"""
        # TODO: Implement validation
        return True

    def set_validation_level(self, level: str) -> "ConfigManager":
        """Set the validation level

        Args:
            level: Validation level (strict, warn, ignore)

        Returns:
            Self for method chaining
        """
        if level not in (
            ValidationLevel.STRICT,
            ValidationLevel.WARN,
            ValidationLevel.IGNORE,
        ):
            raise ValueError(f"Invalid validation level: {level}")

        self._validation_level = level
        return self

    def _handle_validation_error(self, message: str) -> bool:
        """Handle validation error based on validation level

        Args:
            message: Error message

        Returns:
            False if in STRICT mode, True otherwise
        """
        if self._validation_level == ValidationLevel.STRICT:
            raise ValueError(message)
        elif self._validation_level == ValidationLevel.WARN:
            log.warning(f"Configuration validation: {message}")

        return self._validation_level != ValidationLevel.STRICT
