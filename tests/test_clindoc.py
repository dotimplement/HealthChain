import pytest

from unittest.mock import Mock


def test_initialization(clindoc):
    assert clindoc._service_api is not None
    assert isinstance(clindoc.service_config, dict)
    assert clindoc._service is not None
    assert clindoc._client is not None
    assert "service_mount" in clindoc.endpoints


def test_clindoc_notereader(clindoc, test_cda_request, test_cda_response):
    clindoc._service_api.func.return_value = test_cda_response
    response = clindoc.process_notereader_document(test_cda_request)

    assert (
        "<ClinicalDocument>Mock CDA Response Document</ClinicalDocument>"
        in response.document
    )


def test_cds_service_incorrect_return_type(clindoc, test_cda_request):
    clindoc._service_api.func.return_value = "this is not a valid return type"
    with pytest.raises(TypeError):
        clindoc.process_notereader_document(test_cda_request)


def test_cds_service_incorrect_number_of_parameters(clindoc, test_cda_request):
    def func_zero_params():
        pass

    def func_two_params(self, param1, param2):
        pass

    # Test with zero parameters apart from 'self'
    clindoc._service_api = Mock(func=func_zero_params)
    with pytest.raises(AssertionError):
        clindoc.process_notereader_document(test_cda_request)

    # Test with more than one parameter apart from 'self'
    clindoc._service_api = Mock(func=func_two_params)
    with pytest.raises(AssertionError):
        clindoc.process_notereader_document(test_cda_request)
