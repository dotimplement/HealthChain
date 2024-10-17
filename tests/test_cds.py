import pytest

from unittest.mock import Mock
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse


def test_initialization(cds):
    assert cds._service_api is not None
    assert isinstance(cds.service_config, dict)
    assert cds._service is not None
    assert cds._client is not None
    assert "info" in cds.endpoints
    assert "service_mount" in cds.endpoints


def test_cds_discovery_client_not_set(cds):
    cds._client = None
    info = cds.cds_discovery()
    assert info.services == []


def test_cds_discovery(cds):
    cds_info = cds.cds_discovery()
    assert len(cds_info.services) == 1
    assert cds_info.services[0].id == "1"
    assert cds_info.services[0].hook == "hook1"


def test_cds_service_valid_response(
    cds,
    test_cds_request,
    test_cds_response_single_card,
    test_cds_response_multiple_cards,
):
    # Test when everything is valid
    def valid_service_func_single_card(self, request: CDSRequest):
        return test_cds_response_single_card

    cds._service_api = Mock(func=valid_service_func_single_card)

    response = cds.cds_service("1", test_cds_request)
    assert response == test_cds_response_single_card

    def valid_service_func_multiple_cards(self, request: CDSRequest):
        return test_cds_response_multiple_cards

    cds._service_api = Mock(func=valid_service_func_multiple_cards)

    response = cds.cds_service("1", test_cds_request)
    assert response == test_cds_response_multiple_cards


def test_cds_service_no_service_api(cds, test_cds_request):
    # Test when _service_api is None
    cds._service_api = None
    response = cds.cds_service("test_id", test_cds_request)
    assert isinstance(response, CDSResponse)
    assert response.cards == []


def test_cds_service_invalid(cds, test_cds_request, test_cds_response_empty):
    # Test when service_api function has invalid signature
    def invalid_service_signature(self, invalid_param: str):
        return test_cds_response_empty

    cds._service_api = Mock(func=invalid_service_signature)

    with pytest.raises(
        TypeError, match="Expected first argument of service function to be CDSRequest"
    ):
        cds.cds_service("test_id", test_cds_request)

    # Test when service_api function has invalid number of parameters
    def invalid_service_num_params(self):
        return test_cds_response_empty

    cds._service_api = Mock(func=invalid_service_num_params)

    with pytest.raises(
        AssertionError,
        match="Service function must have at least one parameter besides 'self'",
    ):
        cds.cds_service("test_id", test_cds_request)

    # Test when service_api function returns invalid type
    def invalid_service_return_type(self, request: CDSRequest):
        return "Not a CDSResponse"

    cds._service_api = Mock(func=invalid_service_return_type)

    with pytest.raises(TypeError, match="Expected CDSResponse, but got str"):
        cds.cds_service("test_id", test_cds_request)

    # test no annotation - should not raise error
    def valid_service_func_no_annotation(self, request):
        return test_cds_response_empty

    cds._service_api = Mock(func=valid_service_func_no_annotation)

    assert cds.cds_service("test_id", test_cds_request) == test_cds_response_empty
