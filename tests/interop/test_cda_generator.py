import pytest
from unittest.mock import Mock, patch

from healthchain.interop.generators.cda import (
    CDAGenerator,
    _find_section_key_for_resource_type,
)


@pytest.fixture
def mock_fhir_resources():
    """Create mock FHIR resources for testing."""
    return [
        {
            "resourceType": "Condition",
            "id": "example1",
            "subject": {"reference": "Patient/123"},
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "123456",
                        "display": "Test Problem",
                    }
                ]
            },
        },
        {
            "resourceType": "MedicationStatement",
            "id": "example2",
            "subject": {"reference": "Patient/123"},
            "medication": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": "789",
                        "display": "Test Medication",
                    }
                ]
            },
        },
        {
            "resourceType": "Observation",  # This won't map to any section
            "id": "example3",
            "subject": {"reference": "Patient/123"},
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "55423-8",
                        "display": "Test Observation",
                    }
                ]
            },
        },
    ]


@pytest.fixture
def mock_config_manager():
    """Create a mock configuration manager."""
    config = Mock()

    # Configure document config method
    config.get_cda_document_config.side_effect = lambda doc_type: {
        "ccd": {
            "code": {
                "code": "34133-9",
                "display": "Summarization of Episode Note",
                "system": "2.16.840.1.113883.6.1",
            },
            "templates": {"document": "cda_document", "section": "cda_section"},
            "sections": ["problems", "medications"],
            "structure": {
                "body": {
                    "include_sections": ["problems", "medications"],
                }
            },
        }
    }.get(doc_type, {})

    # Configure section configs method
    section_configs = {
        "problems": {
            "resource": "Condition",
            "identifiers": {
                "code": "11450-4",
                "display": "Problem List",
                "system": "2.16.840.1.113883.6.1",
            },
            "template": "problem_entry",
        },
        "medications": {
            "resource": "MedicationStatement",
            "identifiers": {
                "code": "10160-0",
                "display": "Medication List",
                "system": "2.16.840.1.113883.6.1",
            },
            "template": "medication_entry",
        },
    }
    config.get_cda_section_configs.return_value = section_configs

    # Configure get_mappings method
    config.get_mappings.return_value = {}

    # Configure get_config_value method
    config.get_config_value.side_effect = lambda key, default=None: {
        "defaults.common.id_prefix": "test-",
        "defaults.common.subject": {"reference": "Patient/123"},
        "defaults.common.timestamp": "%Y%m%d",
        "defaults.common.reference_name": "#{uuid}name",
        "cda.document.ccd.templates.document": "cda_document",
        "cda.document.ccd.templates.section": "cda_section",
        "cda.document.ccd.rendering.xml.pretty_print": True,
        "cda.document.ccd.rendering.xml.encoding": "UTF-8",
    }.get(key, default)

    return config


@pytest.fixture
def mock_template_registry():
    """Create a mock template registry."""
    registry = Mock()
    registry.get_template.return_value = "mock_template"

    # Mock the render method
    registry.render.return_value = "<xml>Rendered template</xml>"

    return registry


@pytest.fixture
def cda_generator(mock_config_manager, mock_template_registry):
    """Create a CDAGenerator with mocked dependencies."""
    generator = CDAGenerator(mock_config_manager, mock_template_registry)

    # Mock get_template_from_section_config
    generator.get_template_from_section_config = Mock(return_value="mock_template")

    # Mock get_template
    generator.get_template = Mock(return_value="mock_template")

    # Mock render_template
    generator.render_template = Mock(
        return_value={
            "ClinicalDocument": {"id": "test123", "code": {"code": "34133-9"}}
        }
    )

    return generator


def test_find_section_key_for_resource_type():
    """Test the _find_section_key_for_resource_type helper function."""
    section_configs = {
        "problems": {"resource": "Condition"},
        "medications": {"resource": "MedicationStatement"},
    }

    # Test finding a mapped resource type
    assert (
        _find_section_key_for_resource_type("Condition", section_configs) == "problems"
    )

    # Test finding another mapped resource type
    assert (
        _find_section_key_for_resource_type("MedicationStatement", section_configs)
        == "medications"
    )

    # Test with an unmapped resource type
    assert _find_section_key_for_resource_type("Observation", section_configs) is None


def test_initialization(mock_config_manager, mock_template_registry):
    """Test basic initialization of CDAGenerator."""
    generator = CDAGenerator(mock_config_manager, mock_template_registry)
    assert generator.config is mock_config_manager
    assert generator.template_registry is mock_template_registry


def test_generate_document_from_fhir_resources(cda_generator, mock_fhir_resources):
    """Test generating a CDA document from FHIR resources."""
    # Mock the _get_mapped_entries method
    with patch.object(cda_generator, "_get_mapped_entries") as mock_get_mapped:
        mock_get_mapped.return_value = {
            "problems": [{"title": "Test Problem", "code": "123456"}],
            "medications": [{"title": "Test Medication", "code": "789"}],
        }

        # Mock the _render_sections method
        with patch.object(cda_generator, "_render_sections") as mock_render_sections:
            mock_render_sections.return_value = [
                {"section": "problems"},
                {"section": "medications"},
            ]

            # Mock the _render_document method
            with patch.object(cda_generator, "_render_document") as mock_render_doc:
                mock_render_doc.return_value = (
                    "<ClinicalDocument>Test content</ClinicalDocument>"
                )

                # Call the method
                result = cda_generator.generate_document_from_fhir_resources(
                    mock_fhir_resources, "ccd"
                )

                # Verify _get_mapped_entries was called with document_type
                mock_get_mapped.assert_called_once_with(mock_fhir_resources, "ccd")

                # Verify _render_sections was called
                mock_render_sections.assert_called_once()

                # Verify _render_document was called
                mock_render_doc.assert_called_once()

                # Verify result
                assert result == "<ClinicalDocument>Test content</ClinicalDocument>"


def test_get_mapped_entries(cda_generator, mock_fhir_resources):
    """Test mapping FHIR resources to CDA section entries."""
    # Mock _render_entry
    with patch.object(cda_generator, "_render_entry") as mock_render_entry:
        # Return different values for each resource type
        mock_render_entry.side_effect = [
            {"id": "entry1", "resource_type": "Condition"},
            {"id": "entry2", "resource_type": "MedicationStatement"},
            None,  # For the Observation which shouldn't map
        ]

        # Mock _find_section_key_for_resource_type
        with patch(
            "healthchain.interop.generators.cda._find_section_key_for_resource_type"
        ) as mock_find:
            mock_find.side_effect = ["problems", "medications", None]

            # Mock the config manager's get_cda_document_config method
            cda_generator.config.get_cda_document_config.return_value = {
                "structure": {"body": {"include_sections": ["problems", "medications"]}}
            }

            # Call the method with document_type
            result = cda_generator._get_mapped_entries(mock_fhir_resources, "ccd")

            # Verify result contains expected sections
            assert "problems" in result
            assert "medications" in result

            # Verify entries were added to the correct sections
            assert len(result["problems"]) == 1
            assert result["problems"][0]["id"] == "entry1"

            assert len(result["medications"]) == 1
            assert result["medications"][0]["id"] == "entry2"

            # Verify _render_entry was called the right number of times
            assert mock_render_entry.call_count == 2

            # Verify find_section_key_for_resource_type was called for each resource
            assert mock_find.call_count == 3


def test_render_entry(cda_generator):
    """Test rendering a CDA entry from a FHIR resource."""
    # Create a mock resource
    resource = Mock()
    resource.model_dump.return_value = {
        "resourceType": "Condition",
        "id": "test-id",
        "subject": {"reference": "Patient/123"},
    }

    # Call the method
    result = cda_generator._render_entry(resource, "problems")

    # Verify template was retrieved
    cda_generator.get_template_from_section_config.assert_called_with(
        "problems", "entry"
    )

    # Verify render_template was called with correct context
    render_call = cda_generator.render_template.call_args
    assert render_call[0][0] == "mock_template"  # Template
    assert "resource" in render_call[0][1]  # Context
    assert "config" in render_call[0][1]  # Context

    # Verify result
    assert result == {
        "ClinicalDocument": {"code": {"code": "34133-9"}, "id": "test123"}
    }


def test_render_entry_with_missing_template(cda_generator):
    """Test rendering an entry with missing template."""
    # Create a mock resource
    resource = Mock()
    resource.model_dump.return_value = {"id": "test"}

    # Set up the mock to return None for template
    cda_generator.get_template_from_section_config.return_value = None

    # Call the method
    result = cda_generator._render_entry(resource, "unknown_section")

    # Verify no result was returned
    assert result is None


def test_render_sections(cda_generator):
    """Test rendering CDA sections."""
    # Create test data
    mapped_entries = {"problems": [{"id": "problem1"}], "medications": [{"id": "med1"}]}

    # Call the method
    cda_generator._render_sections(mapped_entries, "ccd")

    # Verify get_template was called
    cda_generator.get_template.assert_called_with("cda_section")

    # Verify render_template was called for each section
    assert cda_generator.render_template.call_count == 2


def test_render_sections_with_missing_template(cda_generator):
    """Test rendering sections with missing template."""
    # First set up the get_config_value to return a template name
    cda_generator.config.get_config_value.return_value = "some_template"

    # Then set up the mock to return None for template
    cda_generator.get_template.return_value = None

    # Verify an error is raised
    with pytest.raises(ValueError, match="Required template"):
        cda_generator._render_sections({}, "ccd")


def test_render_document(cda_generator):
    """Test rendering a CDA document."""
    # Create test data
    sections = [{"section": "problems"}, {"section": "medications"}]

    # Mock xmltodict.unparse
    with patch("healthchain.interop.generators.cda.xmltodict.unparse") as mock_unparse:
        mock_unparse.return_value = "<ClinicalDocument>Test XML</ClinicalDocument>"

        # Mock ClinicalDocument validation
        with patch(
            "healthchain.interop.generators.cda.ClinicalDocument"
        ) as mock_validator:
            mock_validator_instance = Mock()
            mock_validator_instance.model_dump.return_value = {"validated": "document"}
            mock_validator.return_value = mock_validator_instance

            # Call the method
            cda_generator._render_document(sections, "ccd")

            # Verify get_template was called
            cda_generator.get_template.assert_called_with("cda_document")

            # Verify render_template was called with sections
            render_call = cda_generator.render_template.call_args
            assert render_call[0][0] == "mock_template"  # Template
            assert "sections" in render_call[0][1]  # Context
            assert (
                render_call[0][1]["sections"] == sections
            )  # Sections passed in context

            # Verify validation was called - with the dictionary from rendered["ClinicalDocument"]
            mock_validator.assert_called_once_with(
                id="test123", code={"code": "34133-9"}
            )

            # Verify xmltodict.unparse was called
            mock_unparse.assert_called_once()


def test_render_document_without_validation(cda_generator):
    """Test rendering a document without validation."""
    # Create test data
    sections = [{"section": "test"}]

    # Mock xmltodict.unparse
    with patch("healthchain.interop.generators.cda.xmltodict.unparse") as mock_unparse:
        mock_unparse.return_value = "<ClinicalDocument>Test XML</ClinicalDocument>"

        # Mock ClinicalDocument validation - should not be called
        with patch(
            "healthchain.interop.generators.cda.ClinicalDocument"
        ) as mock_validator:
            # Call the method with validate=False
            cda_generator._render_document(sections, "ccd", validate=False)

            # Verify validator was not called
            mock_validator.assert_not_called()

            # Verify xmltodict.unparse was called with rendered template
            mock_unparse.assert_called_once()


def test_render_document_with_missing_template(cda_generator):
    """Test rendering a document with missing template."""
    # Mock document config to return a valid config
    cda_generator.config.get_cda_document_config.return_value = {
        "templates": {"document": "test_template"}
    }

    # First set up the get_config_value to return a template name
    cda_generator.config.get_config_value.return_value = "some_template"

    # Then set up the mock to return None for template
    cda_generator.get_template.return_value = None

    # Verify an error is raised
    with pytest.raises(ValueError, match="Required template"):
        cda_generator._render_document([], "ccd")


def test_generate_document_with_invalid_type(cda_generator):
    """Test generating a document with an invalid document type."""
    # Test the _render_document method directly since that's where the first error should be raised
    # Mock the config to return empty dict for the invalid document type
    cda_generator.config.get_cda_document_config.side_effect = ValueError(
        "Document configuration not found for type: invalid_type"
    )

    # Verify that a ValueError is raised with the expected message
    with pytest.raises(
        ValueError,
        match="Failed to load document configuration: Document configuration not found for type: invalid_type",
    ):
        cda_generator._render_document([], "invalid_type")


def test_transform_method(cda_generator, mock_fhir_resources):
    """Test the transform method that implements the BaseGenerator abstract method."""
    # Mock the generate_document_from_fhir_resources method
    with patch.object(
        cda_generator, "generate_document_from_fhir_resources"
    ) as mock_generate:
        mock_generate.return_value = "<ClinicalDocument>Transformed</ClinicalDocument>"

        # Call the transform method
        result = cda_generator.transform(mock_fhir_resources, document_type="ccd")

        # Verify the correct method was called with parameters
        mock_generate.assert_called_once_with(mock_fhir_resources, "ccd")

        # Verify the result
        assert result == "<ClinicalDocument>Transformed</ClinicalDocument>"

        # Test with default document type
        cda_generator.transform(mock_fhir_resources)
        mock_generate.assert_called_with(mock_fhir_resources, "ccd")
