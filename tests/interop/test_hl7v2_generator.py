import pytest
from unittest.mock import Mock
from fhir.resources.resource import Resource
from healthchain.interop.generators.hl7v2 import HL7v2Generator


@pytest.fixture
def mock_config_manager():
    """Create a mock configuration manager."""
    config = Mock()
    config.get_config_value.side_effect = lambda key, default=None: {
        "defaults.common.id_prefix": "test-",
    }.get(key, default)
    return config


@pytest.fixture
def mock_template_registry():
    """Create a mock template registry."""
    registry = Mock()
    registry.get_template.return_value = "mock_template"
    registry.render.return_value = "MSH|^~\\&|SENDER|SENDER|RECEIVER|RECEIVER|123|"
    return registry


@pytest.fixture
def hl7v2_generator(mock_config_manager, mock_template_registry):
    """Create a HL7v2Generator with mocked dependencies."""
    generator = HL7v2Generator(mock_config_manager, mock_template_registry)

    # Mock the generate_message_from_fhir_resource method
    generator.generate_message_from_fhir_resource = Mock(
        return_value="MSH|^~\\&|SENDER|SENDER|RECEIVER|RECEIVER|test-123|"
    )

    return generator


def test_initialization(mock_config_manager, mock_template_registry):
    """Test basic initialization of HL7v2Generator."""
    generator = HL7v2Generator(mock_config_manager, mock_template_registry)
    assert generator.config is mock_config_manager
    assert generator.template_registry is mock_template_registry


def test_transform_method(hl7v2_generator):
    """Test the transform method that implements the BaseGenerator abstract method."""
    # Create a mock resource
    mock_resource = Mock(spec=Resource)
    mock_resource.id = "123"

    # Test transformation
    result = hl7v2_generator.transform(mock_resource)

    # Verify correct method was called
    hl7v2_generator.generate_message_from_fhir_resource.assert_called_once_with(
        mock_resource
    )

    # Verify result
    assert result == "MSH|^~\\&|SENDER|SENDER|RECEIVER|RECEIVER|test-123|"


def test_generate_message_from_fhir_resource():
    """Test generating a message from a FHIR resource."""
    # Create config and registry mocks
    config = Mock()
    registry = Mock()

    # Create a real generator (not mocked)
    generator = HL7v2Generator(config, registry)

    # Create a mock resource
    mock_resource = Mock(spec=Resource)
    mock_resource.id = "test-456"

    # Test generating a message
    message = generator.generate_message_from_fhir_resource(mock_resource)

    # Verify result contains the resource ID
    assert mock_resource.id in message
    assert message.startswith("MSH|")
