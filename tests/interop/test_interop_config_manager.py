import pytest
import tempfile

from pathlib import Path
from unittest.mock import patch, MagicMock

from healthchain.config.base import ValidationLevel
from healthchain.interop.config_manager import InteropConfigManager


# Mocks for validation functions
@pytest.fixture
def mock_validators():
    """Mock the validation functions."""
    with patch(
        "healthchain.interop.config_manager.validate_cda_section_config_model"
    ) as mock_section_validator, patch(
        "healthchain.interop.config_manager.validate_cda_document_config_model"
    ) as mock_doc_validator:
        # Configure mocks to return True by default
        mock_section_validator.return_value = True
        mock_doc_validator.return_value = True

        yield {"section": mock_section_validator, "document": mock_doc_validator}


def test_interop_config_manager_initialization(config_fixtures):
    """Test initialization of InteropConfigManager."""
    config_dir = config_fixtures

    # Test with default params
    manager = InteropConfigManager(config_dir)
    assert manager._validation_level == ValidationLevel.STRICT
    assert manager._module == "interop"
    assert manager._environment == "development"

    # Test with custom environment
    manager = InteropConfigManager(
        config_dir, validation_level=ValidationLevel.WARN, environment="production"
    )
    assert manager._validation_level == ValidationLevel.WARN
    assert manager._environment == "production"


def test_get_cda_section_configs(config_fixtures):
    """Test getting section configurations."""
    config_dir = config_fixtures

    # Create manager - validation happens at initialization
    manager = InteropConfigManager(config_dir)

    # Get section configs
    sections = manager.get_cda_section_configs()

    # Check if sections were loaded correctly
    assert "problems" in sections
    assert sections["problems"]["resource"] == "Condition"
    assert sections["problems"]["identifiers"]["display"] == "Problem List"

    assert "medications" in sections
    assert sections["medications"]["resource"] == "MedicationStatement"


def test_get_document_config(config_fixtures, mock_validators):
    """Test getting document configurations."""
    config_dir = config_fixtures

    # Reset and configure validators to succeed
    mock_validators["section"].return_value = True
    mock_validators["document"].return_value = True

    # Create manager - validation happens at initialization
    manager = InteropConfigManager(config_dir)

    # Get document config
    ccd_config = manager.get_cda_document_config("ccd")

    # Check if document config was loaded correctly
    assert ccd_config["code"]["code"] == "34133-9"
    assert ccd_config["code"]["display"] == "Summarization of Episode Note"
    assert ccd_config["templates"]["section"] == "cda_section"

    # Also verify document types can be found (replaces test_find_document_types)
    document_types = manager._find_cda_document_types()
    assert "ccd" in document_types


def test_validation_behavior(config_fixtures, mock_validators):
    """Test validation behavior with different levels and explicit validation."""
    config_dir = config_fixtures

    # Test 1: STRICT validation failure during initialization
    mock_validators["section"].return_value = False
    with pytest.raises(ValueError):
        InteropConfigManager(config_dir, validation_level=ValidationLevel.STRICT)

    # Test 2: WARN validation - should not raise exception despite validation failure
    manager = InteropConfigManager(config_dir, validation_level=ValidationLevel.WARN)
    assert manager._loaded  # Should still load despite validation failure

    # Test 3: IGNORE validation - shouldn't call validators at all
    mock_validators["section"].reset_mock()
    mock_validators["document"].reset_mock()

    manager = InteropConfigManager(config_dir, validation_level=ValidationLevel.IGNORE)
    assert manager._loaded
    assert mock_validators["section"].call_count == 0

    # Test 4: Explicit validation with different levels
    mock_validators["section"].reset_mock()
    mock_validators["section"].return_value = False

    # With STRICT validation, should raise exception on explicit validate()
    manager._validation_level = ValidationLevel.STRICT
    with pytest.raises(ValueError):
        manager.validate()

    # With WARN validation, should return False to indicate validation failed but execution continues
    manager._validation_level = ValidationLevel.WARN
    assert manager.validate() is False

    # With IGNORE validation, should always return True regardless of validation result
    manager._validation_level = ValidationLevel.IGNORE
    assert manager.validate() is True


def test_registration_methods():
    """Test registration methods for custom models."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)

        # Create minimal interop directory structure
        interop_dir = config_dir / "interop"
        interop_dir.mkdir(parents=True)

        # Create manager with IGNORE validation to simplify test
        with patch(
            "healthchain.interop.config_manager.register_cda_section_template_config_model"
        ) as mock_register_section_config, patch(
            "healthchain.interop.config_manager.register_cda_document_template_config_model"
        ) as mock_register_document_config:
            manager = InteropConfigManager(
                config_dir, validation_level=ValidationLevel.IGNORE
            )

            # Register models and verify registration calls
            model = MagicMock()
            manager.register_cda_section_config("Condition", model)
            manager.register_cda_document_config("ccd", model)

            mock_register_section_config.assert_called_once_with("Condition", model)
            mock_register_document_config.assert_called_once_with("ccd", model)


def test_with_real_configs(real_config_dir, mock_validators):
    """Test with real configuration files."""
    # Configure validators to succeed
    mock_validators["section"].return_value = True
    mock_validators["document"].return_value = True

    # Create manager with IGNORE validation to focus on structure tests
    manager = InteropConfigManager(
        real_config_dir, validation_level=ValidationLevel.IGNORE
    )

    # Test 1: Check section configs
    sections = manager.get_cda_section_configs()
    assert len(sections) > 0

    # Check at least one section has expected structure
    for section_name, section in sections.items():
        assert "resource" in section
        assert "identifiers" in section
        break

    # Test 2: Check document configs
    document_types = manager._find_cda_document_types()
    assert len(document_types) > 0

    if "ccd" in document_types:
        ccd_config = manager.get_cda_document_config("ccd")
        assert "code" in ccd_config
        assert "code" in ccd_config["code"]
