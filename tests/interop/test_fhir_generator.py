import pytest
from unittest.mock import Mock, patch

from healthchain.interop.generators.fhir import FHIRGenerator
from healthchain.interop.types import FormatType


@pytest.fixture
def mock_config_manager():
    """Create a mock configuration manager."""
    config = Mock()
    config.get_config_value.side_effect = lambda key, default=None: {
        "cda.sections.problems.resource": "Condition",
        "cda.sections.medications.resource": "MedicationStatement",
        "cda.sections.allergies.resource": "AllergyIntolerance",
        "defaults.common.id_prefix": "test-",
        "defaults.common.subject": {"reference": "Patient/123"},
        "defaults.resources.Condition.clinicalStatus": {"coding": [{"code": "active"}]},
        "defaults.resources.MedicationStatement.status": "active",
        "defaults.resources.AllergyIntolerance.clinicalStatus": {
            "coding": [{"code": "active"}]
        },
    }.get(key, default)

    config.get_cda_section_configs.return_value = {
        "code": {"code": "11450-4"},
        "title": "Problems",
        "resource": "Condition",
    }
    return config


@pytest.fixture
def mock_template_registry():
    """Create a mock template registry."""
    registry = Mock()
    registry.get_template.return_value = "mock_template"
    registry.render.return_value = {
        "resourceType": "Condition",
        "subject": {"reference": "Patient/123"},
    }
    return registry


@pytest.fixture
def fhir_generator(mock_config_manager, mock_template_registry):
    """Create a FHIRGenerator with mocked dependencies."""
    generator = FHIRGenerator(mock_config_manager, mock_template_registry)
    # Mock get_template_from_section_config
    generator.get_template_from_section_config = Mock(return_value="mock_template")
    # Mock render_template
    generator.render_template = Mock(
        return_value={
            "resourceType": "Condition",
            "subject": {"reference": "Patient/123"},
        }
    )
    return generator


def test_generate_resources_from_cda_section_entries(fhir_generator):
    """Test generating resources from CDA section entries."""
    # Prepare test data
    entries = [{"id": "entry1", "data": "value1"}, {"id": "entry2", "data": "value2"}]
    section_key = "problems"

    # Mock _validate_fhir_resource
    with patch.object(fhir_generator, "_validate_fhir_resource") as mock_validate:
        # Return a valid resource for each call
        mock_validate.side_effect = [
            {
                "resourceType": "Condition",
                "id": "test-1",
                "subject": {"reference": "Patient/123"},
            },
            {
                "resourceType": "Condition",
                "id": "test-2",
                "subject": {"reference": "Patient/123"},
            },
        ]

        # Call the method
        resources = fhir_generator.generate_resources_from_cda_section_entries(
            entries, section_key
        )

        # Verify results
        assert len(resources) == 2
        assert mock_validate.call_count == 2

        # Verify template was used
        fhir_generator.get_template_from_section_config.assert_called_with(
            section_key, "resource"
        )

        # Verify _render_resource_from_entry was called for each entry
        assert fhir_generator.render_template.call_count == 2


def test_generate_resources_missing_template(fhir_generator):
    """Test handling when no template is found."""
    # Set up the mock to return None for template
    fhir_generator.get_template_from_section_config.return_value = None

    # Call the method
    resources = fhir_generator.generate_resources_from_cda_section_entries(
        [{"id": "entry1"}], "unknown_section"
    )

    # Verify no resources were created
    assert len(resources) == 0

    # Verify template lookup was attempted
    fhir_generator.get_template_from_section_config.assert_called_with(
        "unknown_section", "resource"
    )


def test_generate_resources_missing_resource_type(fhir_generator):
    """Test handling when no resource type is specified."""
    # Set up the mock to return None for resource type
    fhir_generator.config.get_config_value.side_effect = (
        lambda key, default=None: None
        if key == "sections.unknown_section.resource"
        else "default"
    )

    # Call the method
    resources = fhir_generator.generate_resources_from_cda_section_entries(
        [{"id": "entry1"}], "unknown_section"
    )

    # Verify no resources were created
    assert len(resources) == 0


def test_render_resource_from_entry(fhir_generator):
    """Test rendering a FHIR resource from a CDA entry."""
    # Prepare test data
    entry = {"id": "entry1", "data": "value1"}
    section_key = "problems"

    # Call the method
    resource = fhir_generator._render_resource_from_entry(
        entry, section_key, "mock_template"
    )

    # Verify the correct context was passed to render_template
    expected_context = {
        "entry": entry,
        "config": fhir_generator.config.get_cda_section_configs.return_value,
    }
    fhir_generator.render_template.assert_called_with("mock_template", expected_context)

    # Verify the result
    assert resource == {
        "resourceType": "Condition",
        "subject": {"reference": "Patient/123"},
    }


def test_render_resource_with_section_config_error(fhir_generator):
    """Test handling when section config raises error."""
    # Set up the mock to raise an error
    fhir_generator.config.get_cda_section_configs.side_effect = ValueError(
        "Config error"
    )

    # Call the method
    resource = fhir_generator._render_resource_from_entry(
        {"id": "entry1"}, "problems", "mock_template"
    )

    # Verify no resource was created
    assert resource is None


def test_validate_fhir_resource(fhir_generator):
    """Test validating a FHIR resource dictionary."""
    # Prepare test data
    resource_dict = {
        "resourceType": "Condition",
        "subject": {"reference": "Patient/123"},
    }

    # Mock create_resource_from_dict
    with patch(
        "healthchain.interop.generators.fhir.create_resource_from_dict"
    ) as mock_create:
        mock_create.return_value = {
            "resourceType": "Condition",
            "id": "test-uuid",
            "subject": {"reference": "Patient/123"},
        }

        # Call the method
        resource = fhir_generator._validate_fhir_resource(resource_dict, "Condition")

        # Verify _add_required_fields was called
        assert resource is not None
        mock_create.assert_called_once()


def test_validate_fhir_resource_failure(fhir_generator):
    """Test handling validation failure."""
    # Prepare test data
    resource_dict = {"invalid": "resource"}

    # Mock create_resource_from_dict to raise an exception
    with patch(
        "healthchain.interop.generators.fhir.create_resource_from_dict"
    ) as mock_create:
        mock_create.side_effect = ValueError("Invalid resource")

        # Call the method
        resource = fhir_generator._validate_fhir_resource(resource_dict, "Condition")

        # Verify no resource was created
        assert resource is None


def test_add_required_fields_condition(fhir_generator):
    """Test adding required fields to a Condition resource."""
    # Prepare minimal resource
    resource_dict = {"resourceType": "Condition"}

    # Call the method
    result = fhir_generator._add_required_fields(resource_dict, "Condition")

    # Verify fields were added
    assert "id" in result
    assert result["id"].startswith("test-")
    assert "subject" in result
    assert result["subject"] == {"reference": "Patient/123"}
    assert "clinicalStatus" in result
    assert result["clinicalStatus"] == {"coding": [{"code": "active"}]}


def test_add_required_fields_medication_statement(fhir_generator):
    """Test adding required fields to a MedicationStatement resource."""
    # Prepare minimal resource
    resource_dict = {"resourceType": "MedicationStatement"}

    # Call the method
    result = fhir_generator._add_required_fields(resource_dict, "MedicationStatement")

    # Verify fields were added
    assert "id" in result
    assert result["id"].startswith("test-")
    assert "subject" in result
    assert result["subject"] == {"reference": "Patient/123"}
    assert "status" in result
    assert result["status"] == "active"


def test_add_required_fields_allergy_intolerance(fhir_generator):
    """Test adding required fields to an AllergyIntolerance resource."""
    # Prepare minimal resource
    resource_dict = {"resourceType": "AllergyIntolerance"}

    # Call the method
    result = fhir_generator._add_required_fields(resource_dict, "AllergyIntolerance")

    # Verify fields were added
    assert "id" in result
    assert result["id"].startswith("test-")
    assert "patient" in result
    assert result["patient"] == {"reference": "Patient/123"}
    assert "clinicalStatus" in result
    assert result["clinicalStatus"] == {"coding": [{"code": "active"}]}


def test_add_required_fields_with_existing_values(fhir_generator):
    """Test that existing values are not overwritten."""
    # Prepare resource with existing values
    resource_dict = {
        "resourceType": "Condition",
        "id": "existing-id",
        "subject": {"reference": "Patient/456"},
        "clinicalStatus": {"coding": [{"code": "resolved"}]},
    }

    # Call the method
    result = fhir_generator._add_required_fields(resource_dict, "Condition")

    # Verify fields were not changed
    assert result["id"] == "existing-id"
    assert result["subject"] == {"reference": "Patient/456"}
    assert result["clinicalStatus"] == {"coding": [{"code": "resolved"}]}


def test_add_required_fields_unknown_resource_type(fhir_generator):
    """Test handling unknown resource types."""
    # Prepare minimal resource
    resource_dict = {"resourceType": "UnknownType"}

    # Call the method
    result = fhir_generator._add_required_fields(resource_dict, "UnknownType")

    # Verify only common fields were added
    assert "id" in result
    assert result["id"].startswith("test-")
    assert "subject" not in result  # Not added for unknown types


def test_transform_method(fhir_generator):
    """Test the transform method that implements the BaseGenerator abstract method."""
    # Mock the generate_resources_from_cda_section_entries method
    with patch.object(
        fhir_generator, "generate_resources_from_cda_section_entries"
    ) as mock_cda_generate:
        mock_cda_generate.return_value = [{"resourceType": "Condition", "id": "test-1"}]

        # Mock the generate_resources_from_hl7v2_entries method
        with patch.object(
            fhir_generator, "generate_resources_from_hl7v2_entries"
        ) as mock_hl7v2_generate:
            mock_hl7v2_generate.return_value = [
                {"resourceType": "Observation", "id": "test-2"}
            ]

            # Test CDA transformation
            entries = [{"id": "entry1", "data": "value1"}]
            result = fhir_generator.transform(
                entries, src_format=FormatType.CDA, section_key="problems"
            )

            # Verify correct method was called
            mock_cda_generate.assert_called_once_with(entries, "problems")
            assert result == [{"resourceType": "Condition", "id": "test-1"}]

            # Test HL7v2 transformation
            entries = [{"id": "entry2", "data": "value2"}]
            result = fhir_generator.transform(
                entries, src_format=FormatType.HL7V2, message_key="observations"
            )

            # Verify correct method was called
            mock_hl7v2_generate.assert_called_once_with(entries, "observations")
            assert result == [{"resourceType": "Observation", "id": "test-2"}]

            # Test with invalid format
            with pytest.raises(ValueError):
                fhir_generator.transform(entries, src_format="invalid")
