import os
import pytest
from pathlib import Path
from unittest.mock import patch

from healthchain.config.base import (
    ConfigManager,
    ValidationLevel,
    _deep_merge,
    _get_nested_value,
)


# Test utility functions - essential foundation
def test_utility_functions():
    """Test utility functions for deep merging and nested access."""
    # Test deep_merge
    target = {"a": 1, "b": {"c": 2, "d": 3}}
    source = {"b": {"e": 4}, "f": 5}
    _deep_merge(target, source)
    assert target == {"a": 1, "b": {"c": 2, "d": 3, "e": 4}, "f": 5}

    # Test _get_nested_value
    data = {"a": 1, "b": {"c": 2, "d": {"e": 3}}}
    assert _get_nested_value(data, ["a"]) == 1
    assert _get_nested_value(data, ["b", "c"]) == 2
    assert _get_nested_value(data, ["b", "d", "e"]) == 3
    assert _get_nested_value(data, ["x"]) is None  # Missing key


# Core functionality tests
def test_config_manager_initialization(config_fixtures):
    """Test initialization and environment detection."""
    config_dir = config_fixtures

    # Test with default params
    manager = ConfigManager(config_dir)
    assert manager._validation_level == ValidationLevel.STRICT
    assert manager._module is None
    assert manager._environment == "development"  # Default

    # Test with custom params
    manager = ConfigManager(
        config_dir, validation_level=ValidationLevel.WARN, module="interop"
    )
    assert manager._validation_level == ValidationLevel.WARN
    assert manager._module == "interop"

    # Test environment detection
    with patch.dict(os.environ, {"HEALTHCHAIN_ENV": "production"}):
        manager = ConfigManager(Path("/fake/path"))
        assert manager._environment == "production"

    # Test invalid environment falls back to default
    with patch.dict(os.environ, {"HEALTHCHAIN_ENV": "invalid_env"}):
        manager = ConfigManager(Path("/fake/path"))
        assert manager._environment == "development"


def test_config_loading_and_access(config_fixtures):
    """Test loading configurations and accessing values."""
    config_dir = config_fixtures

    # Test loading defaults and environment configs
    manager = ConfigManager(config_dir)
    manager.load()

    # Test defaults are loaded
    assert manager._defaults["defaults"]["common"]["id_prefix"] == "hc-"

    # Test environment config is loaded
    assert manager._env_configs["debug"] is True

    # Test loading with explicit environment
    manager = ConfigManager(config_dir)
    manager.load(environment="production")
    assert manager._environment == "production"
    assert manager._env_configs["database"]["host"] == "db.example.com"

    # Test getting values with precedence
    assert (
        manager.get_config_value("defaults.common.id_prefix") == "hc-"
    )  # From defaults
    assert (
        manager.get_config_value("database.name") == "healthchain_prod"
    )  # From environment
    assert (
        manager.get_config_value("nonexistent.key", "default") == "default"
    )  # Default value

    # Test module configs
    manager = ConfigManager(config_dir, module="interop")
    manager.load()
    configs = manager.get_configs()

    # Check sections are available
    assert "cda" in configs
    assert "sections" in configs["cda"]
    assert configs["cda"]["sections"]["problems"]["resource"] == "Condition"

    # Check document configs are nested properly
    assert "document" in configs["cda"]
    assert configs["cda"]["document"]["ccd"]["code"]["code"] == "34133-9"

    # Test mappings access - was test_load_mappings
    mappings = manager.get_mappings()
    assert "snomed_loinc" in mappings
    assert mappings["snomed_loinc"]["snomed_to_loinc"]["55607006"] == "11450-4"


def test_validation_and_error_handling(config_fixtures):
    """Test validation levels and error handling."""
    config_dir = config_fixtures

    # Test validation levels
    manager = ConfigManager(config_dir, validation_level=ValidationLevel.STRICT)
    assert manager._validation_level == ValidationLevel.STRICT

    manager = ConfigManager(config_dir, validation_level=ValidationLevel.WARN)
    assert manager._validation_level == ValidationLevel.WARN

    manager = ConfigManager(config_dir, validation_level=ValidationLevel.IGNORE)
    assert manager._validation_level == ValidationLevel.IGNORE

    # Test setting validation level
    manager.set_validation_level(ValidationLevel.WARN)
    assert manager._validation_level == ValidationLevel.WARN

    # Test invalid validation level
    with pytest.raises(ValueError):
        manager.set_validation_level("invalid_level")

    # Test error handling with missing files
    config_dir = config_fixtures

    # Remove defaults file if it exists
    defaults_file = config_dir / "defaults.yaml"
    if defaults_file.exists():
        temp_content = defaults_file.read_bytes()  # Save content to restore later
        defaults_file.unlink()
        try:
            manager = ConfigManager(config_dir)
            manager.load()
            # Should work but with empty defaults
            assert manager._defaults == {}
        finally:
            # Restore the file
            defaults_file.write_bytes(temp_content)

    # Test nonexistent environment
    manager = ConfigManager(config_dir)
    manager.load(environment="nonexistent")
    # Should have empty env configs but not fail
    assert manager._env_configs == {}


# Simplified real-world test
def test_with_real_configs(real_config_dir):
    """Test with real configuration files."""
    # Create manager with IGNORE validation to focus on structure
    manager = ConfigManager(real_config_dir, validation_level=ValidationLevel.IGNORE)
    manager.load()

    # Test 1: Check basic configs
    assert manager._defaults
    assert "defaults" in manager._defaults
    assert manager._env_configs

    # Test 2: Check module configs if available
    if real_config_dir.joinpath("interop").exists():
        manager = ConfigManager(
            real_config_dir, module="interop", validation_level=ValidationLevel.IGNORE
        )
        manager.load()
        configs = manager.get_configs()

        # Verify expected structure exists
        assert "cda" in configs


def test_runtime_configuration_overrides(config_fixtures):
    """Test setting and getting runtime configuration overrides."""
    config_dir = config_fixtures

    # Initialize config manager and load defaults
    manager = ConfigManager(config_dir)
    manager.load()

    # Test 1: Basic setting and getting of runtime value
    manager.set_config_value("test.key", "test_value")
    assert manager.get_config_value("test.key") == "test_value"

    # Test 2: Override an existing value from defaults
    original_id_prefix = manager.get_config_value("defaults.common.id_prefix")
    assert original_id_prefix == "hc-"  # Verify original value

    manager.set_config_value("defaults.common.id_prefix", "override-")
    assert manager.get_config_value("defaults.common.id_prefix") == "override-"

    # Test 3: Setting nested configuration values
    manager.set_config_value("nested.config.test", {"key1": "value1", "key2": "value2"})
    nested_value = manager.get_config_value("nested.config.test")
    assert nested_value["key1"] == "value1"
    assert nested_value["key2"] == "value2"

    # Test 4: Verify runtime overrides in merged configs
    manager.set_config_value("database.name", "runtime_db")
    configs = manager.get_configs()
    assert configs["database"]["name"] == "runtime_db"

    # Test 5: Verify precedence (runtime override > environment > defaults)
    # First set the environment to production
    manager.set_environment("production")
    # Environment config should have database.name = "healthchain_prod"
    assert manager._env_configs["database"]["name"] == "healthchain_prod"
    # But runtime override should take precedence
    assert manager.get_config_value("database.name") == "runtime_db"

    # Test 6: Test method chaining
    result = manager.set_config_value("chain.test", "value1").set_config_value(
        "chain.test2", "value2"
    )
    assert result is manager  # Should return self
    assert manager.get_config_value("chain.test") == "value1"
    assert manager.get_config_value("chain.test2") == "value2"
