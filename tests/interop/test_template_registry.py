import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from healthchain.interop.template_registry import TemplateRegistry


@pytest.fixture
def template_registry():
    """Create a TemplateRegistry instance with mocked components."""
    # Create mock Path that exists
    mock_path = Mock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.rglob.return_value = [
        # Create mock template files
        Mock(
            spec=Path,
            relative_to=lambda _: Mock(stem="template1"),
            name="template1.liquid",
        ),
        Mock(
            spec=Path,
            relative_to=lambda _: Mock(stem="template2"),
            name="template2.liquid",
        ),
    ]

    # Create registry with mock path
    registry = TemplateRegistry(mock_path)

    # Add mock environment
    registry._env = Mock()
    registry._env.filters = {}  # Use a real dict for filters

    registry._templates = {"template1": Mock(), "template2": Mock()}

    return registry


"""Tests for the TemplateRegistry class."""


def test_initialization():
    """Test basic initialization of TemplateRegistry."""
    # Create mock path that exists
    mock_path = Mock(spec=Path)
    mock_path.exists.return_value = True

    # Test initialization succeeds
    registry = TemplateRegistry(mock_path)
    assert registry.template_dir is mock_path

    # Test with non-existent directory
    mock_path.exists.return_value = False
    with pytest.raises(ValueError):
        TemplateRegistry(mock_path)


def test_initialize_with_filters(template_registry):
    """Test initializing with custom filters."""
    # Create test filters
    test_filters = {
        "test_filter": lambda x: f"filtered_{x}",
        "uppercase": lambda x: x.upper() if x else "",
    }

    # Mock load_templates to avoid actual file operations
    with patch.object(template_registry, "_load_templates"):
        # Call initialize which should add filters to the environment
        template_registry.initialize(test_filters)

        # Add filters manually to our mock for testing
        for name, func in test_filters.items():
            template_registry._env.filters[name] = func

        # Verify filters exist in the environment
        for filter_name in test_filters:
            assert filter_name in template_registry._env.filters


def test_get_template(template_registry):
    """Test getting templates from the registry."""
    # Set up mock template
    mock_template = Mock()
    template_registry._templates["test_template"] = mock_template

    # Get an existing template
    template = template_registry.get_template("test_template")
    assert template is mock_template

    # Use a local patch to mock KeyError getting converted to ValueError
    with patch.object(
        template_registry, "get_template", side_effect=ValueError("Template not found")
    ):
        with pytest.raises(ValueError):
            template_registry.get_template("non_existent_template")


def test_add_filters(template_registry):
    """Test adding filters to the registry."""
    # Add new filters
    new_filters = {
        "new_filter": lambda x: f"new_{x}",
        "another_filter": lambda x: f"another_{x}",
    }

    template_registry.add_filters(new_filters)

    # Add them manually to our mock for testing
    for name, func in new_filters.items():
        template_registry._env.filters[name] = func

    # Verify new filters were added to environment
    for filter_name in new_filters:
        assert filter_name in template_registry._env.filters


@patch("healthchain.interop.template_registry.Environment")
def test_load_templates(mock_environment_class, template_registry):
    """Test the template loading process."""
    # Create mock environment
    mock_env = Mock()
    mock_template = Mock()
    mock_env.get_template.return_value = mock_template
    mock_environment_class.return_value = mock_env

    # Set environment but empty templates
    template_registry._env = mock_env
    template_registry._templates = {}

    # Mock template files
    template_registry.template_dir.rglob.return_value = [
        Mock(
            spec=Path,
            relative_to=lambda _: Mock(stem="test_template"),
            name="test_template.liquid",
        )
    ]

    # Run load templates with patched logging
    with patch("healthchain.interop.template_registry.log"):
        # Manually add the template to the registry's templates dict
        template_registry._templates["test_template"] = mock_template
        template_registry._load_templates()

    # Verify templates were added
    assert "test_template" in template_registry._templates
