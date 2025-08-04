"""Tests for interop initialization functions."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from healthchain.interop import init_config_templates, create_interop
from healthchain.interop.engine import InteropEngine


def test_init_config_templates_prevents_overwriting_existing_configs():
    """init_config_templates prevents accidentally overwriting existing configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        target_dir = Path(temp_dir) / "existing"
        target_dir.mkdir()  # Create directory first

        with pytest.raises(FileExistsError, match="Target directory already exists"):
            init_config_templates(str(target_dir))


def test_init_config_templates_creates_customizable_config_structure():
    """init_config_templates creates complete configuration structure for user customization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create minimal mock source structure
        source_dir = Path(temp_dir) / "source"
        source_dir.mkdir()
        (source_dir / "defaults.yaml").write_text("version: 1.0")

        target_dir = Path(temp_dir) / "target"

        with patch("healthchain.interop._get_bundled_configs", return_value=source_dir):
            result = init_config_templates(str(target_dir))

        # Verify structure is created and files are copied
        assert result == target_dir
        assert target_dir.exists()
        assert (target_dir / "defaults.yaml").exists()


def test_init_config_templates_handles_copy_failures_gracefully():
    """init_config_templates provides clear error message when copy operation fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        nonexistent_source = Path(temp_dir) / "nonexistent"
        target_dir = Path(temp_dir) / "target"

        with patch(
            "healthchain.interop._get_bundled_configs", return_value=nonexistent_source
        ):
            with pytest.raises(OSError, match="Failed to copy configuration templates"):
                init_config_templates(str(target_dir))


@pytest.mark.parametrize("environment", ["invalid_env", "staging", "local"])
def test_create_interop_validates_environment_parameter(environment):
    """create_interop enforces valid environment values for configuration consistency."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with pytest.raises(ValueError, match="environment must be one of"):
            create_interop(config_dir=temp_dir, environment=environment)


def test_create_interop_rejects_nonexistent_config_directory():
    """create_interop validates config directory exists before engine creation."""
    nonexistent_dir = Path("/nonexistent/path")

    with pytest.raises(ValueError, match="Config directory does not exist"):
        create_interop(config_dir=nonexistent_dir)


@patch("healthchain.interop.InteropEngine")
def test_create_interop_supports_custom_validation_and_environment_settings(
    mock_engine_class,
):
    """create_interop passes validation and environment settings to engine for proper configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        mock_engine = Mock(spec=InteropEngine)
        mock_engine_class.return_value = mock_engine

        result = create_interop(
            config_dir=temp_dir, validation_level="warn", environment="testing"
        )

        # Verify configuration is passed correctly
        mock_engine_class.assert_called_once_with(Path(temp_dir), "warn", "testing")
        assert result == mock_engine


@patch("healthchain.interop.InteropEngine")
def test_create_interop_auto_discovers_configuration_when_none_specified(
    mock_engine_class,
):
    """create_interop automatically finds and uses available configuration when no config_dir provided."""
    mock_engine = Mock(spec=InteropEngine)
    mock_engine_class.return_value = mock_engine

    # Should successfully create engine with auto-discovered configs
    result = create_interop()

    # Verify engine was created (discovery mechanism is implementation detail)
    mock_engine_class.assert_called_once()
    assert result == mock_engine
