import pytest
from unittest.mock import Mock, patch
from abc import ABC

from healthchain.interop.generators.base import BaseGenerator


# Create a concrete subclass for testing the abstract base class
class ConcreteTestGenerator(BaseGenerator):
    def transform(self, data, **kwargs):
        """Concrete implementation for testing"""
        return f"transformed: {data}"


@pytest.fixture
def mock_template_registry():
    """Create a mock template registry."""
    registry = Mock()

    # Mock get_template to return a template object
    mock_template = Mock()
    mock_template.render.return_value = '{"key": "value"}'
    mock_template.name = "test_template"
    registry.get_template.return_value = mock_template
    registry.has_template.return_value = True

    return registry


@pytest.fixture
def mock_config():
    """Create a mock config manager."""
    config = Mock()
    config.get_config_value.return_value = "test_template"
    config.get_cda_section_configs.return_value = {
        "problems": {"resource": "Condition"},
        "medications": {"resource": "MedicationStatement"},
    }
    return config


@pytest.fixture
def test_generator(mock_config, mock_template_registry):
    """Create a concrete ConcreteTestGenerator instance with mocked dependencies."""
    return ConcreteTestGenerator(mock_config, mock_template_registry)


def test_initialization(mock_config, mock_template_registry):
    """Test basic initialization of BaseGenerator."""
    generator = ConcreteTestGenerator(mock_config, mock_template_registry)
    assert generator.config is mock_config
    assert generator.template_registry is mock_template_registry


def test_get_template(test_generator, mock_template_registry):
    """Test getting a template by name."""
    # Test getting an existing template
    template = test_generator.get_template("test_template")
    assert template is mock_template_registry.get_template.return_value

    # Test with non-existent template
    mock_template_registry.get_template.side_effect = KeyError("Template not found")
    template = test_generator.get_template("non_existent_template")
    assert template is None

    # Reset side effect
    mock_template_registry.get_template.side_effect = None


def test_get_template_from_section_config(
    test_generator, mock_config, mock_template_registry
):
    """Test getting a template from section configuration."""
    # Test 1: Getting a valid template
    mock_config.get_config_value.return_value = "/path/to/problem_entry"
    mock_template_registry.has_template.return_value = True

    template = test_generator.get_template_from_section_config("problems", "entry")

    # Verify config was called correctly
    mock_config.get_config_value.assert_called_with(
        "cda.sections.problems.entry_template"
    )

    # Verify template registry was used correctly
    mock_template_registry.has_template.assert_called_with("/path/to/problem_entry")
    mock_template_registry.get_template.assert_called_with("/path/to/problem_entry")

    assert template is mock_template_registry.get_template.return_value

    # Test 2: Missing template in config
    mock_config.get_config_value.return_value = None
    template = test_generator.get_template_from_section_config("missing", "entry")
    assert template is None

    # Test 3: Template not in registry
    mock_config.get_config_value.return_value = "/path/to/unknown_template"
    mock_template_registry.has_template.return_value = False
    template = test_generator.get_template_from_section_config("problems", "resource")
    assert template is None


def test_render_template(test_generator, mock_template_registry):
    """Test rendering a template with context."""
    # Define test context
    context = {"key": "value", "items": [1, 2, 3]}

    # Get a template
    template = mock_template_registry.get_template.return_value

    # Render the template
    result = test_generator.render_template(template, context)

    # Verify template's render method was called with the context
    template.render.assert_called_once_with(context)

    # Verify the result is the parsed JSON
    assert result == {"key": "value"}


@patch("healthchain.interop.generators.base.log")
def test_render_template_error_handling(
    mock_log, test_generator, mock_template_registry
):
    """Test error handling during template rendering."""
    # Get a template
    template = mock_template_registry.get_template.return_value

    # Configure template to raise an error during rendering
    template.render.side_effect = Exception("Rendering error")

    # Render the template with error
    result = test_generator.render_template(template, {"key": "value"})

    # Verify error was logged
    mock_log.error.assert_called()

    # Verify result is None
    assert result is None


def test_transform_method(test_generator):
    """Test that the transform method works correctly in the concrete subclass."""
    result = test_generator.transform("test_data", extra_param="value")
    assert result == "transformed: test_data"


def test_base_generator_is_abstract():
    """Test that BaseGenerator is an abstract class and can't be instantiated directly."""
    assert issubclass(BaseGenerator, ABC)

    # Attempting to instantiate BaseGenerator should raise TypeError
    with pytest.raises(TypeError):
        BaseGenerator(Mock(), Mock())
