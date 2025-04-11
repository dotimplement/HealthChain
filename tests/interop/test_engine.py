import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from healthchain.interop.engine import (
    InteropEngine,
    normalize_resource_list,
)
from healthchain.interop.types import FormatType, validate_format
from healthchain.config.base import ValidationLevel

from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement


@pytest.fixture
def mock_config_manager():
    """Create a mock InteropConfigManager."""
    config = Mock()
    config._validation_level = ValidationLevel.IGNORE
    config._environment = "testing"
    config.get_mappings.return_value = {}
    config.get_cda_section_configs.return_value = {
        "problems": {"resource": "Condition"},
        "medications": {"resource": "MedicationStatement"},
    }
    config.get_cda_document_configs.return_value = {
        "ccd": {"resource": "ClinicalDocument"}
    }
    return config


@pytest.fixture
def mock_template_registry():
    """Create a mock TemplateRegistry."""
    registry = Mock()
    registry.initialize.return_value = None
    registry.render_template.return_value = "<xml>Rendered template</xml>"
    return registry


@pytest.fixture
def interop_engine(mock_config_manager, mock_template_registry):
    """Create a mocked InteropEngine instance for testing."""
    with patch(
        "healthchain.interop.engine.InteropConfigManager",
        return_value=mock_config_manager,
    ), patch(
        "healthchain.interop.engine.TemplateRegistry",
        return_value=mock_template_registry,
    ):
        engine = InteropEngine(
            config_dir=Path("/mock/path"),
            validation_level=ValidationLevel.IGNORE,
            environment="testing",
        )
        # Set mocked components
        engine.config = mock_config_manager
        engine.template_registry = mock_template_registry
        return engine


# TODO: might be able to reuse fixtures
@pytest.fixture
def mock_fhir_resources():
    """Mock FHIR resources for testing."""
    return [
        {
            "resourceType": "Condition",
            "id": "example",
            "subject": {"reference": "Patient/123"},
        }
    ]


@pytest.fixture
def mock_cda_document():
    """Mock CDA document for testing."""
    return "<ClinicalDocument>Test CDA Content</ClinicalDocument>"


def test_normalize_resource_list(test_condition, test_condition_list, test_bundle):
    """Test normalize_resource_list with different input types"""
    # Test with single resource
    result = normalize_resource_list(test_condition)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == test_condition

    # Test with list of resources
    result = normalize_resource_list(test_condition_list)
    assert result is test_condition_list
    assert len(result) == 2

    # Test with Bundle
    result = normalize_resource_list(test_bundle)
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], Condition)
    assert isinstance(result[1], MedicationStatement)


def test_validate_format():
    """Test format type validation - more complete tests"""
    # Test with enum values
    assert validate_format(FormatType.FHIR) == FormatType.FHIR
    assert validate_format(FormatType.CDA) == FormatType.CDA
    assert validate_format(FormatType.HL7V2) == FormatType.HL7V2

    # Test with string values (case insensitive)
    assert validate_format("fhir") == FormatType.FHIR
    assert validate_format("FHIR") == FormatType.FHIR
    assert validate_format("Fhir") == FormatType.FHIR

    assert validate_format("cda") == FormatType.CDA
    assert validate_format("CDA") == FormatType.CDA

    assert validate_format("hl7v2") == FormatType.HL7V2
    assert validate_format("HL7V2") == FormatType.HL7V2

    # Test with invalid formats
    with pytest.raises(ValueError, match="Unsupported format: invalid"):
        validate_format("invalid")


def test_register_custom_parser(interop_engine):
    """Test registering a custom parser."""
    mock_parser = Mock()
    interop_engine.register_parser(FormatType.CDA, mock_parser)

    # The registered parser should be returned when accessed
    assert interop_engine._get_parser(FormatType.CDA) is mock_parser


def test_register_custom_generator(interop_engine):
    """Test registering a custom generator."""
    mock_generator = Mock()
    interop_engine.register_generator(FormatType.FHIR, mock_generator)

    # The registered generator should be returned when accessed
    assert interop_engine._get_generator(FormatType.FHIR) is mock_generator


def test_register_validators(interop_engine):
    """Test registering custom validators."""
    # Test registering template validator
    mock_template_model = Mock()
    interop_engine.register_cda_section_config_validator(
        "Condition", mock_template_model
    )

    # Test registering document validator
    mock_document_model = Mock()
    interop_engine.register_cda_document_config_validator("ccd", mock_document_model)

    # Verify registration methods were called
    interop_engine.config.register_cda_section_config.assert_called_with(
        "Condition", mock_template_model
    )
    interop_engine.config.register_cda_document_config.assert_called_with(
        "ccd", mock_document_model
    )


def test_to_fhir_from_cda(interop_engine, mock_cda_document, mock_fhir_resources):
    """Test converting from CDA to FHIR."""
    # Mock the CDA parser
    mock_cda_parser = Mock()
    mock_cda_parser.from_string.return_value = {"problems": ["test_entry"]}
    interop_engine._parsers[FormatType.CDA] = mock_cda_parser

    # Mock the FHIR generator
    mock_fhir_generator = Mock()
    mock_fhir_generator.transform.return_value = mock_fhir_resources
    interop_engine._generators[FormatType.FHIR] = mock_fhir_generator

    # Mock the cached property access
    interop_engine.cda_parser = mock_cda_parser
    interop_engine.fhir_generator = mock_fhir_generator

    # Test conversion with _cda_to_fhir directly since to_fhir depends on it
    result = interop_engine._cda_to_fhir(mock_cda_document)

    # Verify parser was called with correct input
    mock_cda_parser.from_string.assert_called_once_with(mock_cda_document)

    # Verify generator was called with transform
    mock_fhir_generator.transform.assert_called_with(
        ["test_entry"], src_format=FormatType.CDA, section_key="problems"
    )

    # Verify result matches expected output
    assert result == mock_fhir_resources


def test_from_fhir_to_cda(interop_engine, mock_fhir_resources, mock_cda_document):
    """Test converting from FHIR to CDA."""
    # Mock the CDA generator
    mock_cda_generator = Mock()
    mock_cda_generator.transform.return_value = mock_cda_document
    interop_engine._generators[FormatType.CDA] = mock_cda_generator

    # Mock cached property access
    interop_engine.cda_generator = mock_cda_generator

    # Mock config.get_document_config
    interop_engine.config.get_cda_document_config.return_value = {
        "code": {"code": "34133-9"}
    }
    interop_engine.config.get_config_value.return_value = "cda_document"

    # Test conversion with _fhir_to_cda directly
    result = interop_engine._fhir_to_cda(mock_fhir_resources, document_type="ccd")

    # Verify config was called to get document config
    interop_engine.config.get_cda_document_config.assert_called_with("ccd")

    # Verify generator was called with transform method
    mock_cda_generator.transform.assert_called_once_with(
        mock_fhir_resources, document_type="ccd"
    )

    # Verify result matches expected output
    assert result == mock_cda_document


def test_to_fhir_with_unsupported_format(interop_engine, mock_cda_document):
    """Test to_fhir with unsupported format."""
    with pytest.raises(ValueError):
        interop_engine.to_fhir(mock_cda_document, src_format="invalid")


def test_from_fhir_with_unsupported_format(interop_engine, mock_fhir_resources):
    """Test from_fhir with unsupported format."""
    with pytest.raises(ValueError):
        interop_engine.from_fhir(mock_fhir_resources, dest_format="invalid")


# def test_fhir_to_hl7v2(interop_engine, mock_fhir_resources):
#     """Test converting from FHIR to HL7v2."""
#     # Mock the HL7v2 generator
#     mock_hl7v2_generator = Mock()
#     mock_hl7v2_generator.transform.return_value = "MSH|^~\\&|SENDER|RECEIVER|"
#     interop_engine._generators[FormatType.HL7V2] = mock_hl7v2_generator

#     # Mock cached property access
#     interop_engine.hl7v2_generator = mock_hl7v2_generator

#     # Test conversion
#     result = interop_engine._fhir_to_hl7v2(mock_fhir_resources)

#     # Verify generator was called with transform method
#     assert mock_hl7v2_generator.transform.call_count == len(mock_fhir_resources)

#     # Verify result is a list of messages
#     assert isinstance(result, list)
#     assert all(isinstance(msg, str) for msg in result)


# def test_hl7v2_to_fhir(interop_engine, mock_fhir_resources):
#     """Test converting from HL7v2 to FHIR."""
#     # Mock the HL7v2 parser
#     mock_hl7v2_parser = Mock()
#     mock_hl7v2_parser.from_string.return_value = {"observations": ["test_entry"]}
#     interop_engine._parsers[FormatType.HL7V2] = mock_hl7v2_parser

#     # Mock the FHIR generator
#     mock_fhir_generator = Mock()
#     mock_fhir_generator.transform.return_value = mock_fhir_resources
#     interop_engine._generators[FormatType.FHIR] = mock_fhir_generator

#     # Mock the cached property access
#     interop_engine.hl7v2_parser = mock_hl7v2_parser
#     interop_engine.fhir_generator = mock_fhir_generator

#     # Test conversion
#     result = interop_engine._hl7v2_to_fhir("MSH|^~\\&|SENDER|RECEIVER|")

#     # Verify parser was called with correct input
#     mock_hl7v2_parser.from_string.assert_called_once_with("MSH|^~\\&|SENDER|RECEIVER|")

#     # Verify generator was called with transform
#     mock_fhir_generator.transform.assert_called_with(
#         ["test_entry"],
#         src_format=FormatType.HL7V2,
#         message_key="observations"
#     )

#     # Verify result matches expected output
#     assert result == mock_fhir_resources
