import yaml
import logging
import os
from pathlib import Path
from typing import Dict, Any, Set, Optional, List

log = logging.getLogger(__name__)


class ValidationLevel:
    """Validation levels for configuration"""

    STRICT = "strict"  # Raise exceptions for missing or invalid config
    WARN = "warn"  # Log warnings but continue
    IGNORE = "ignore"  # Skip validation entirely


class ConfigManager:
    """Manages loading and accessing configuration files for the InteropEngine"""

    # TODO: Use Pydantic to validate config files

    # Define required configuration schemas
    REQUIRED_SECTION_KEYS = {
        "resource",
        "resource_template",
        "entry_template",
        "section_template_id",
        "code",
        "display",
    }

    REQUIRED_DOCUMENT_KEYS = {
        "type_id",
        "code",
        "confidentiality_code",
    }

    def __init__(
        self, config_dir: Path, validation_level: str = ValidationLevel.STRICT
    ):
        """Initialize the ConfigManager

        Args:
            config_dir: Base directory containing configuration files
            validation_level: Level of validation to perform (strict, warn, ignore)
        """
        self.config_dir = config_dir
        self._configs = {}
        self._mappings = {}
        self._defaults = {}
        self._env_configs = {}
        self._loaded = False
        self._validation_level = validation_level
        self._custom_schemas = {}
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
        """Load all configuration files

        Args:
            environment: Optional environment to load (overrides auto-detection)

        Returns:
            Self for method chaining
        """
        # Set environment if provided
        if environment:
            self._environment = environment

        # Load defaults first
        self._load_defaults()

        # Load environment-specific configuration
        self._load_environment_config()

        # Load other configurations
        self._mappings = self._load_directory("mappings")
        self._configs = self._load_directory("configs")
        self._loaded = True

        # Validate configurations if not in IGNORE mode
        if self._validation_level != ValidationLevel.IGNORE:
            self.validate()

        return self

    def _load_defaults(self) -> None:
        """Load the defaults.yaml file if it exists"""
        defaults_file = self.config_dir / "configs" / "defaults.yaml"
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
        env_file = self.config_dir / "configs" / f"{self._environment}.yaml"
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

    def _load_directory(self, directory: str) -> Dict:
        """Load all YAML files from a directory

        Args:
            directory: Directory name relative to config_dir

        Returns:
            Dict of loaded configurations
        """
        configs = {}
        config_dir = self.config_dir / directory

        if not config_dir.exists():
            log.warning(f"Configuration directory not found: {config_dir}")
            return configs

        for config_file in config_dir.rglob("*.yaml"):
            # Skip defaults.yaml and environment files as they're loaded separately
            if directory == "configs":
                if config_file.name == "defaults.yaml":
                    continue
                if config_file.name in [
                    "development.yaml",
                    "testing.yaml",
                    "production.yaml",
                ]:
                    continue

            try:
                with open(config_file) as f:
                    # Get relative path from configs directory for hierarchical keys
                    if directory == "configs":
                        rel_path = config_file.relative_to(config_dir)
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
                            self._deep_merge(configs, current_level)
                        else:
                            # Top-level file, just use the stem as key
                            configs[config_file.stem] = content
                    else:
                        # For non-configs directories, use the old behavior
                        configs[config_file.stem] = yaml.safe_load(f)

                log.debug(f"Loaded configuration file: {config_file}")
            except Exception as e:
                log.error(f"Failed to load configuration file {config_file}: {str(e)}")

        return configs

    def _deep_merge(self, target: Dict, source: Dict) -> None:
        """Deep merge source dictionary into target dictionary

        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                # If both are dictionaries, recursively merge
                self._deep_merge(target[key], value)
            else:
                # Otherwise, overwrite the value
                target[key] = value

    def get_mappings(self) -> Dict:
        """Get all mappings

        Returns:
            Dict of mappings
        """
        if not self._loaded:
            self.load()
        return self._mappings

    def get_configs(self) -> Dict:
        """Get all configs

        Returns:
            Dict of configs
        """
        if not self._loaded:
            self.load()

        # Create a merged configuration with the correct precedence:
        # 1. Regular configs (highest priority)
        # 2. Environment-specific configs
        # 3. Default configs (lowest priority)
        merged_configs = {}

        # Start with defaults
        self._deep_merge(merged_configs, self._defaults)

        # Apply environment-specific configs
        self._deep_merge(merged_configs, self._env_configs)

        # Apply regular configs
        self._deep_merge(merged_configs, self._configs)

        return merged_configs

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

    def get_section_configs(self) -> Dict:
        """Get section configurations

        Returns:
            Dict of section configurations
        """
        return self.get_configs().get("sections", {})

    def get_document_config(self) -> Dict:
        """Get document configuration

        Returns:
            Document configuration dict
        """
        return self.get_configs().get("document", {}).get("cda", {})

    def get_config_value(self, path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation path

        Args:
            path: Dot notation path (e.g., "section.problems.resource")
            default: Default value if path not found

        Returns:
            Configuration value or default
        """
        if not self._loaded:
            self.load()

        # Split the path into parts
        parts = path.split(".")

        # Get merged configs
        configs = self.get_configs()

        # Get the value from merged configs
        value = self._get_nested_value(configs, parts)
        if value is not None:
            return value

        # Return the provided default if not found
        return default

    def _get_nested_value(self, data: Dict, parts: List[str]) -> Any:
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

    def register_schema(self, config_type: str, required_keys: Set[str]) -> None:
        """Register a custom validation schema

        Args:
            config_type: Type of configuration (e.g., "section", "document")
            required_keys: Set of required keys for this configuration type
        """
        self._custom_schemas[config_type] = required_keys

    def validate(self) -> bool:
        """Validate that all required configurations are present

        Returns:
            True if valid, False otherwise
        """
        is_valid = True

        # Validate section configs
        section_configs = self.get_section_configs()
        if not section_configs:
            is_valid = self._handle_validation_error("No section configs found")
        else:
            # Validate each section
            for section_key, section_config in section_configs.items():
                missing_keys = self.REQUIRED_SECTION_KEYS - set(section_config.keys())
                if missing_keys:
                    is_valid = self._handle_validation_error(
                        f"Section '{section_key}' is missing required keys: {missing_keys}"
                    )

        # Validate document config
        document_config = self.get_document_config()

        if not document_config:
            is_valid = self._handle_validation_error("No document config found")
        else:
            # Validate document config
            missing_keys = self.REQUIRED_DOCUMENT_KEYS - set(document_config.keys())
            if missing_keys:
                is_valid = self._handle_validation_error(
                    f"Document config is missing required keys: {missing_keys}"
                )

        # Validate custom schemas
        for config_type, required_keys in self._custom_schemas.items():
            config = self.get_configs().get(config_type, {})
            if not config:
                is_valid = self._handle_validation_error(
                    f"No {config_type} config found"
                )
                continue

            # If config is a dict of dicts (like sections), validate each sub-config
            if all(isinstance(v, dict) for v in config.values()):
                for key, sub_config in config.items():
                    missing_keys = required_keys - set(sub_config.keys())
                    if missing_keys:
                        is_valid = self._handle_validation_error(
                            f"{config_type.capitalize()} '{key}' is missing required keys: {missing_keys}"
                        )
            else:
                # Validate the config directly
                missing_keys = required_keys - set(config.keys())
                if missing_keys:
                    is_valid = self._handle_validation_error(
                        f"{config_type.capitalize()} config is missing required keys: {missing_keys}"
                    )

        return is_valid

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
