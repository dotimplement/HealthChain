import pytest

from unittest.mock import Mock
from healthchain.use_cases.cds import ClinicalDecisionSupport
from healthchain.models import Card


def test_initialization(cds):
    assert cds.service_api is not None
    assert isinstance(cds.service_config, dict)
    assert cds.service is not None
    assert cds.client is not None
    assert "info" in cds.endpoints
    assert "service_mount" in cds.endpoints


def test_cds_discovery_client_not_set():
    cds = ClinicalDecisionSupport()
    info = cds.cds_discovery()
    assert info.services == []


def test_cds_discovery(cds):
    cds_info = cds.cds_discovery()
    assert len(cds_info.services) == 1
    assert cds_info.services[0].id == "1"
    assert cds_info.services[0].hook == "hook1"


def test_cds_service_no_api_set(test_cds_request):
    cds = ClinicalDecisionSupport()
    response = cds.cds_service("1", test_cds_request)
    assert response.cards == []


def test_cds_service(cds, test_cds_request):
    request = test_cds_request
    cds.service_api.func.return_value = [
        Card(
            summary="example",
            indicator="info",
            source={"label": "test"},
        )
    ]
    response = cds.cds_service("1", request)
    assert len(response.cards) == 1
    assert response.cards[0].summary == "example"
    assert response.cards[0].indicator == "info"


def func_zero_params():
    pass


def func_two_params(self, param1, param2):
    pass


def func_one_param(self, param):
    pass


def test_cds_service_correct_number_of_parameters(cds, test_cds_request):
    # Function with one parameter apart from 'self'
    cds.service_api = Mock(func=func_one_param)

    # Should not raise an assertion error
    cds.cds_service("1", test_cds_request)


def test_cds_service_incorrect_number_of_parameters(cds, test_cds_request):
    # Test with zero parameters apart from 'self'
    cds.service_api = Mock(func=func_zero_params)
    with pytest.raises(AssertionError):
        cds.cds_service("1", test_cds_request)

    # Test with more than one parameter apart from 'self'
    cds.service_api = Mock(func=func_two_params)
    with pytest.raises(AssertionError):
        cds.cds_service("1", test_cds_request)
