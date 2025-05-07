import pytest
from unittest.mock import Mock

from healthchain.interop.parsers.cda import CDAParser
from healthchain.interop.config_manager import InteropConfigManager
from healthchain.interop.models.sections import Section


@pytest.fixture
def sample_cda_document():
    """Create a simple CDA XML document for testing."""
    with open("./tests/data/test_cda.xml", "r") as file:
        test_cda = file.read()

    return test_cda


@pytest.fixture
def mock_config():
    """Create a mock InteropConfigManager."""
    config = Mock(spec=InteropConfigManager)

    # Configure section mapping
    section_config = {
        "problems": {
            "resource": "Condition",
            "identifiers": {
                "template_id": "2.16.840.1.113883.10.20.1.11",
                "code": "11450-4",
                "display": "Problem List",
                "system": "2.16.840.1.113883.6.1",
            },
        },
        "medications": {
            "resource": "MedicationStatement",
            "identifiers": {
                "code": "10160-0",
                "display": "Medication List",
                "system": "2.16.840.1.113883.6.1",
            },
        },
    }

    # Configure get_section_configs method
    config.get_cda_section_configs.return_value = section_config

    # Set up dynamic config_value returns based on input
    def get_config_value(path):
        if path == "cda.sections.problems.identifiers.template_id":
            return "2.16.840.1.113883.10.20.1.11"
        elif path == "cda.sections.problems.identifiers.code":
            return "11450-4"
        elif path == "cda.sections.medications.identifiers.template_id":
            return None
        elif path == "cda.sections.medications.identifiers.code":
            return "10160-0"
        return None

    config.get_config_value.side_effect = get_config_value

    # Configure mapping lookups
    config.get_mappings.return_value = {}

    return config


@pytest.fixture
def cda_parser(mock_config):
    """Create a CDAParser instance with mocked config."""
    return CDAParser(mock_config)


@pytest.fixture
def mock_section():
    """Create a mock section for testing section finding methods."""
    section = Mock(spec=Section)
    return section


def test_initialization(mock_config):
    """Test basic initialization of CDAParser."""
    parser = CDAParser(mock_config)
    assert parser.config is mock_config
    assert parser.clinical_document is None


def test_parse_document(cda_parser, sample_cda_document, mock_config):
    """Test parsing sections from a CDA document."""
    # Parse the document
    sections = cda_parser.parse_document(sample_cda_document)

    # Verify that the problems section was found
    assert "problems" in sections
    assert len(sections["problems"]) > 0

    # Verify that section config was retrieved
    mock_config.get_cda_section_configs.assert_called_once()

    # Check that the clinical document was parsed
    assert cda_parser.clinical_document is not None


def test_parse_document_empty(cda_parser):
    """Test parsing an empty or invalid document."""
    # Test with empty document
    sections = cda_parser.parse_document("")
    assert sections == {}

    # Test with invalid XML
    sections = cda_parser.parse_document("<invalid>XML</not-closed>")
    assert sections == {}


def test_find_section_by_template_id(cda_parser, mock_section):
    """Test finding a section by template ID."""
    # Test when section has matching template ID
    mock_template = Mock()
    mock_template.root = "2.16.840.1.113883.10.20.1.11"
    mock_section.templateId = [mock_template]

    assert (
        cda_parser._find_section_by_template_id(
            mock_section, "2.16.840.1.113883.10.20.1.11"
        )
        is True
    )

    # Test when section has non-matching template ID
    assert (
        cda_parser._find_section_by_template_id(mock_section, "different.template.id")
        is False
    )

    # Test when section has no template ID
    mock_section.templateId = None
    assert cda_parser._find_section_by_template_id(mock_section, "any.id") is False


def test_find_section_by_code(cda_parser, mock_section):
    """Test finding a section by code."""
    # Test when section has matching code
    mock_code = Mock()
    mock_code.code = "11450-4"
    mock_section.code = mock_code

    assert cda_parser._find_section_by_code(mock_section, "11450-4") is True

    # Test when section has non-matching code
    assert cda_parser._find_section_by_code(mock_section, "different-code") is False

    # Test when section has no code
    mock_section.code = None
    assert cda_parser._find_section_by_code(mock_section, "any-code") is False


def test_no_section_found(cda_parser, sample_cda_document, mock_config):
    """Test handling when no sections are defined in the configuration."""
    # Return empty section config to simulate no sections defined
    mock_config.get_cda_section_configs.return_value = {}

    # Parse the document
    sections = cda_parser.parse_document(sample_cda_document)

    # Verify no sections were found
    assert sections == {}


def test_section_defined_but_not_found(cda_parser, sample_cda_document, mock_config):
    """Test handling when sections are defined but not found in the document."""
    # Configure mock to reset side_effect
    mock_config.get_config_value.side_effect = None

    # Configure mock to always return a non-existent identifier
    mock_config.get_config_value.return_value = "definitely.does.not.exist"

    # Ensure we have section configs defined
    section_config = {
        "nonexistent_section": {
            "resource": "NonExistentResource",
            "identifiers": {
                "template_id": "non.existent.template.id",
                "code": "non-existent-code",
            },
        }
    }
    mock_config.get_cda_section_configs.return_value = section_config

    # Parse the document
    sections = cda_parser.parse_document(sample_cda_document)

    # Verify no sections were found
    assert sections == {}
