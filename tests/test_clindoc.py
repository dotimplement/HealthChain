import pytest

from unittest.mock import Mock

from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse


def test_initialization(clindoc):
    assert clindoc._service_api is not None
    assert isinstance(clindoc.service_config, dict)
    assert clindoc._service is not None
    assert clindoc._client is not None
    assert "service_mount" in clindoc.endpoints


def test_clindoc_notereader_service(clindoc, test_cda_request, test_cda_response):
    def valid_service_func(self, request: CdaRequest):
        return test_cda_response

    clindoc._service_api = Mock(func=valid_service_func)
    response = clindoc.process_notereader_document(test_cda_request)

    assert (
        "<ClinicalDocument>Mock CDA Response Document</ClinicalDocument>"
        in response.document
    )


def test_clindoc_service_incorrect_return_type(clindoc, test_cda_request):
    clindoc._service_api.func.return_value = "this is not a valid return type"
    with pytest.raises(TypeError):
        clindoc.process_notereader_document(test_cda_request)


def test_process_notereader_document_no_service_api(clindoc, test_cda_request):
    clindoc._service_api = None
    response = clindoc.process_notereader_document(test_cda_request)
    assert isinstance(response, CdaResponse)
    assert response.document == ""


def test_process_notereader_document_invalid(
    clindoc, test_cda_request, test_cda_response
):
    # Test invalid parameter type
    def invalid_service_func_invalid_param(self, invalid_param: str):
        return test_cda_response

    clindoc._service_api = Mock(func=invalid_service_func_invalid_param)

    with pytest.raises(
        TypeError, match="Expected first argument of service function to be CdaRequest"
    ):
        clindoc.process_notereader_document(test_cda_request)

    # Test invalid return type
    def invalid_service_func_invalid_return_type(self, request: CdaRequest):
        return "Not a CdaResponse"

    clindoc._service_api = Mock(func=invalid_service_func_invalid_return_type)

    with pytest.raises(TypeError, match="Expected return type CdaResponse"):
        clindoc.process_notereader_document(test_cda_request)

    # Test invalid number of parameters
    def invalid_service_func(self):
        return test_cda_response

    clindoc._service_api = Mock(func=invalid_service_func)

    with pytest.raises(
        AssertionError,
        match="Service function must have at least one parameter besides 'self'",
    ):
        clindoc.process_notereader_document(test_cda_request)

    # test no annotation - should not raise error
    def valid_service_func_no_annotation(self, request):
        return test_cda_response

    clindoc._service_api = Mock(func=valid_service_func_no_annotation)

    assert clindoc.process_notereader_document(test_cda_request) == test_cda_response
