import pytest
from unittest.mock import MagicMock

from healthchain.gateway.services.cdshooks import (
    CDSHooksService,
    CDSHooksAdapter,
    CDSHooksConfig,
)
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse, Card
from healthchain.models.responses.cdsdiscovery import CDSServiceInformation


def test_cdshooks_adapter_initialization():
    """Test CDSHooksAdapter initialization with default config"""
    adapter = CDSHooksAdapter()
    assert isinstance(adapter.config, CDSHooksConfig)
    assert adapter.config.system_type == "CDS-HOOKS"
    assert adapter.config.base_path == "/cds"
    assert adapter.config.discovery_path == "/cds-discovery"
    assert adapter.config.service_path == "/cds-services"


def test_cdshooks_adapter_create():
    """Test CDSHooksAdapter.create factory method"""
    adapter = CDSHooksAdapter.create()
    assert isinstance(adapter, CDSHooksAdapter)
    assert isinstance(adapter.config, CDSHooksConfig)


def test_cdshooks_adapter_register_handler():
    """Test handler registration with adapter"""
    adapter = CDSHooksAdapter()
    mock_handler = MagicMock(return_value=CDSResponse(cards=[]))

    # Register handler
    adapter.register_handler(
        operation="patient-view",
        handler=mock_handler,
        id="test-patient-view",
        title="Test Patient View",
        description="Test description",
    )

    # Verify handler is registered
    assert "patient-view" in adapter._handlers
    assert adapter._handlers["patient-view"] == mock_handler

    # Verify metadata is stored
    assert "patient-view" in adapter._handler_metadata
    assert adapter._handler_metadata["patient-view"]["id"] == "test-patient-view"
    assert adapter._handler_metadata["patient-view"]["title"] == "Test Patient View"
    assert (
        adapter._handler_metadata["patient-view"]["description"] == "Test description"
    )


def test_cdshooks_service_initialization():
    """Test CDSHooksService initialization"""
    service = CDSHooksService()
    assert isinstance(service.adapter, CDSHooksAdapter)


def test_cdshooks_service_hook_decorator():
    """Test hook decorator for registering handlers"""
    service = CDSHooksService()

    @service.hook("patient-view", id="test-patient-view")
    def handle_patient_view(request):
        return CDSResponse(cards=[])

    # Verify handler is registered with adapter
    assert "patient-view" in service.adapter._handlers
    assert "patient-view" in service.adapter._handler_metadata
    assert (
        service.adapter._handler_metadata["patient-view"]["id"] == "test-patient-view"
    )
    assert service.adapter._handler_metadata["patient-view"]["title"] == "Patient View"
    assert (
        service.adapter._handler_metadata["patient-view"]["description"]
        == "CDS Hook service created by HealthChain"
    )


def test_cdshooks_adapter_extract_request():
    """Test request extraction from parameters"""
    adapter = CDSHooksAdapter()

    # Case 1: CDSRequest passed directly
    request = CDSRequest(
        hook="patient-view",
        hookInstance="test-instance",
        context={"patientId": "123", "userId": "456"},
    )
    extracted = adapter._extract_request("patient-view", {"request": request})
    assert extracted == request

    # Case 2: CDSRequest as single parameter
    extracted = adapter._extract_request("patient-view", {"param": request})
    assert extracted == request

    # Case 3: Build from params
    adapter.register_handler("patient-view", lambda x: x, id="test")
    extracted = adapter._extract_request(
        "patient-view",
        {
            "hook": "patient-view",
            "hookInstance": "test-instance",
            "context": {"patientId": "123", "userId": "456"},
        },
    )
    assert isinstance(extracted, CDSRequest)
    assert extracted.hook == "patient-view"
    assert extracted.context.patientId == "123"
    assert extracted.context.userId == "456"


def test_cdshooks_adapter_process_result():
    """Test processing results from handlers"""
    adapter = CDSHooksAdapter()

    # Test with CDSResponse object
    response = CDSResponse(
        cards=[Card(summary="Test card", indicator="info", source={"label": "Test"})]
    )
    result = adapter._process_result(response)
    assert isinstance(result, CDSResponse)
    assert len(result.cards) == 1

    # Test with dict containing cards
    result = adapter._process_result(
        {
            "cards": [
                {
                    "summary": "Test card",
                    "indicator": "info",
                    "source": {"label": "Test"},
                }
            ]
        }
    )
    assert isinstance(result, CDSResponse)
    assert len(result.cards) == 1

    # Test with unexpected result type
    result = adapter._process_result("invalid")
    assert isinstance(result, CDSResponse)
    assert len(result.cards) == 0


def test_cdshooks_adapter_handle(test_cds_request):
    """Test handle method with CDSRequest"""
    adapter = CDSHooksAdapter()

    # Register a mock handler
    mock_handler = MagicMock(
        return_value=CDSResponse(
            cards=[
                Card(summary="Test card", indicator="info", source={"label": "Test"})
            ]
        )
    )
    adapter.register_handler("patient-view", mock_handler, id="test")

    # Test handling with request
    result = adapter.handle("patient-view", request=test_cds_request)
    assert isinstance(result, CDSResponse)
    assert len(result.cards) == 1
    assert result.cards[0].summary == "Test card"
    mock_handler.assert_called_once()


def test_cdshooks_service_handle_discovery():
    """Test discovery endpoint handler"""
    service = CDSHooksService()

    # Register sample hooks
    @service.hook("patient-view", id="test-patient-view", title="Patient View")
    def handle_patient_view(request):
        return CDSResponse(cards=[])

    @service.hook("order-select", id="test-order-select", title="Order Select")
    def handle_order_select(request):
        return CDSResponse(cards=[])

    # Get discovery response
    result = service.handle_discovery()
    assert isinstance(result, CDSServiceInformation)
    assert len(result.services) == 2

    # Check if hook information is correctly included
    hooks = {s.hook: s for s in result.services}
    assert "patient-view" in hooks
    assert hooks["patient-view"].id == "test-patient-view"
    assert hooks["patient-view"].title == "Patient View"

    assert "order-select" in hooks
    assert hooks["order-select"].id == "test-order-select"
    assert hooks["order-select"].title == "Order Select"


def test_cdshooks_service_handle_request(test_cds_request):
    """Test request handler endpoint"""
    service = CDSHooksService()

    # Register a mock handler
    @service.hook("patient-view", id="test-patient-view")
    def handle_patient_view(request):
        return CDSResponse(
            cards=[
                Card(
                    summary="Test response", indicator="info", source={"label": "Test"}
                )
            ]
        )

    # Handle request
    result = service.handle_request(test_cds_request)
    assert isinstance(result, CDSResponse)
    assert len(result.cards) == 1
    assert result.cards[0].summary == "Test response"


def test_cdshooks_service_get_routes():
    """Test that CDSHooksService correctly returns routes with get_routes method"""
    service = CDSHooksService()

    # Register sample hooks
    @service.hook("patient-view", id="test-patient-view")
    def handle_patient_view(request):
        return CDSResponse(cards=[])

    # Get routes from service
    routes = service.get_routes()

    # Should return at least 2 routes (discovery endpoint and hook endpoint)
    assert len(routes) >= 2

    # Verify discovery endpoint
    discovery_routes = [r for r in routes if "GET" in r[1]]
    assert len(discovery_routes) >= 1
    discovery_route = discovery_routes[0]
    assert discovery_route[1] == ["GET"]  # HTTP method is GET

    # Verify hook endpoint
    hook_routes = [r for r in routes if "POST" in r[1]]
    assert len(hook_routes) >= 1
    hook_route = hook_routes[0]
    assert hook_route[1] == ["POST"]  # HTTP method is POST
    assert "test-patient-view" in hook_route[0]  # Route path contains hook ID


def test_cdshooks_service_hook_invalid_hook_type():
    """Test hook decorator with invalid hook type"""
    service = CDSHooksService()

    # Try to register an invalid hook type
    with pytest.raises(ValueError):

        @service.hook("invalid-hook-type", id="test")
        def handle_invalid(request):
            return CDSResponse(cards=[])
