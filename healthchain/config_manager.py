import yaml
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from healthchain.config.validators import (
    validate_section_config,
    register_template_model,
    validate_document_config,
    register_document_model,
)

log = logging.getLogger(__name__)


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
        self._configs = {}
        self._mappings = {}
        self._defaults = {}
        self._env_configs = {}
        self._module_configs = {}
        self._module_env_configs = {}
        self._loaded = False
        self._validation_level = validation_level
        self._environment = self._detect_environment()
        self._module = module

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

        # Load project-wide defaults
        self._load_defaults()

        # Load environment-specific configuration
        self._load_environment_config()

        # Load module-specific configs if module is specified
        if self._module:
            self._load_module_configs(self._module)
            self._load_module_environment_config(self._module)

        # Load mappings from the central mappings directory
        self._mappings = self._load_directory("mappings")
        self._loaded = True

        # Validate configurations if not in IGNORE mode
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

        module_configs = {}

        # Load all YAML files in the module directory
        for config_file in module_dir.rglob("*.yaml"):
            # Skip environment-specific files (they're loaded separately)
            if config_file.name.startswith("env_"):
                continue

            try:
                with open(config_file) as f:
                    # Get relative path from module directory for hierarchical keys
                    rel_path = config_file.relative_to(module_dir)
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
                        self._deep_merge(module_configs, current_level)
                    else:
                        # Top-level file, just use the stem as key
                        module_configs[config_file.stem] = content

                log.debug(f"Loaded module configuration file: {config_file}")
            except Exception as e:
                log.error(
                    f"Failed to load module configuration file {config_file}: {str(e)}"
                )

        self._module_configs[module] = module_configs
        log.debug(f"Loaded {len(module_configs)} configurations for module {module}")

    def _load_module_environment_config(self, module: str) -> None:
        """Load module+environment-specific configuration

        Args:
            module: Module name to load configs for
        """
        env_file = self.config_dir / module / f"env_{self._environment}.yaml"

        if env_file.exists():
            try:
                with open(env_file) as f:
                    env_config = yaml.safe_load(f)
                    self._module_env_configs.setdefault(module, {})
                    self._deep_merge(self._module_env_configs[module], env_config)
                log.debug(f"Loaded environment configuration for module {module}")
            except Exception as e:
                log.error(
                    f"Failed to load environment file for module {module}: {str(e)}"
                )
                self._module_env_configs.setdefault(module, {})
        else:
            log.warning(f"Environment file for module {module} not found: {env_file}")
            self._module_env_configs.setdefault(module, {})

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
        """Get all configs with the correct precedence order

        Returns:
            Dict of configs
        """
        if not self._loaded:
            self.load()

        # Create a merged configuration with the correct precedence:
        # 1. Module-specific environment configs (highest priority)
        # 2. Module-specific configs
        # 3. Environment-specific configs
        # 4. Regular configs
        # 5. Default configs (lowest priority)
        merged_configs = {}

        # Start with defaults
        self._deep_merge(merged_configs, self._defaults)

        # Apply regular configs
        self._deep_merge(merged_configs, self._configs)

        # Apply environment-specific configs
        self._deep_merge(merged_configs, self._env_configs)

        # Apply module-specific configs if a module is specified
        if self._module and self._module in self._module_configs:
            self._deep_merge(merged_configs, self._module_configs[self._module])

            # Apply module+environment-specific configs
            if self._module in self._module_env_configs:
                self._deep_merge(merged_configs, self._module_env_configs[self._module])

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

        # Reload module-specific environment configuration if module is set
        if self._module:
            self._load_module_environment_config(self._module)

        return self

    def _find_module_sections(self) -> Dict:
        """Find section configs in the module configs

        Returns:
            Dict of sections, or empty dict if none found
        """
        if not self._module or self._module not in self._module_configs:
            return {}

        # Look for sections directly in module configs
        if "sections" in self._module_configs[self._module]:
            return self._module_configs[self._module]["sections"]

        # Look in subdirectories
        for value in self._module_configs[self._module].values():
            if isinstance(value, dict) and "sections" in value:
                return value["sections"]

        return {}

    def get_section_configs(self, validate: bool = False) -> Dict:
        """Get section configurations

        Args:
            validate: Whether to validate the configurations

        Returns:
            Dict of section configurations
        """
        sections = self._find_module_sections()

        if not sections:
            log.warning("No section configs found")
            return {}

        if not validate:
            return sections

        # Validate each section if requested
        validated_sections = {}
        for section_key, section_config in sections.items():
            if self.validate_section_config(section_key, section_config):
                validated_sections[section_key] = section_config
            elif self._validation_level != ValidationLevel.STRICT:
                # Include the section with warnings if not in STRICT mode
                validated_sections[section_key] = section_config

        return validated_sections

    def get_document_config(self, document_type: str) -> Dict:
        """Get document configuration

        Returns:
            Document configuration dict
        """
        if not self._module or self._module not in self._module_configs:
            log.warning("No document config found")
            return {}

        # Look for document config directly
        if "document" in self._module_configs[self._module]:
            doc_section = self._module_configs[self._module]["document"]
            if isinstance(doc_section, dict) and document_type in doc_section:
                return doc_section[document_type]

        # Look in subdirectories
        for value in self._module_configs[self._module].values():
            if isinstance(value, dict) and "document" in value:
                if (
                    isinstance(value["document"], dict)
                    and document_type in value["document"]
                ):
                    return value["document"][document_type]

        log.warning(f"No document config found for type: {document_type}")
        return {}

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

    def validate_document_config(self, document_type: str) -> bool:
        """Validate document configuration using Pydantic models

        Args:
            document_type: Type of document to validate

        Returns:
            True if valid, False otherwise
        """
        document_config = self.get_document_config(document_type)
        if not document_config:
            self._handle_validation_error(
                f"No document config found for document type: {document_type}"
            )
            return False

        # Validate using Pydantic models
        result = validate_document_config(document_type, document_config)
        if not result and self._validation_level == ValidationLevel.STRICT:
            return False
        return True

    def validate_section_config(self, section_key: str, section_config: Dict) -> bool:
        """Validate a section configuration using Pydantic models

        Args:
            section_key: Name of the section
            section_config: Section configuration dict

        Returns:
            True if valid, False otherwise
        """
        result = validate_section_config(section_key, section_config)
        if not result and self._validation_level == ValidationLevel.STRICT:
            return False
        return True

    def validate(self) -> bool:
        """Validate that all required configurations are present"""
        is_valid = True

        # Validate section configs
        section_configs = self.get_section_configs(validate=True)
        if not section_configs:
            is_valid = self._handle_validation_error("No section configs found")

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

    def register_template_model(self, resource_type: str, template_model) -> None:
        """Register a custom template model

        Args:
            resource_type: FHIR resource type
            template_model: Pydantic model for template validation
        """
        register_template_model(resource_type, template_model)

    def register_document_model(self, document_type: str, document_model) -> None:
        """Register a custom document model

        Args:
            document_type: Document type (e.g., "ccd", "discharge")
            document_model: Pydantic model for document validation
        """
        register_document_model(document_type, document_model)
