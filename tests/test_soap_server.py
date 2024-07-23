import pytest

from unittest.mock import MagicMock
from healthchain.service.soap.model import ClientFault, ServerFault


def test_ProcessDocument_missing_parameters(cdsservices):
    mock_ctx = MagicMock()
    with pytest.raises(ClientFault) as exc_info:
        cdsservices.ProcessDocument(
            mock_ctx, None, "WorkType", "OrganizationID", [b"<xml>...</xml>"]
        )
    assert "Missing required parameter: sessionId" in str(exc_info.value)

    with pytest.raises(ClientFault) as exc_info:
        cdsservices.ProcessDocument(
            mock_ctx, "123456", None, "OrganizationID", [b"<xml>...</xml>"]
        )
    assert "Missing required parameter: workType" in str(exc_info.value)

    with pytest.raises(ClientFault) as exc_info:
        cdsservices.ProcessDocument(
            mock_ctx, "123456", "WorkType", None, [b"<xml>...</xml>"]
        )
    assert "Missing required parameter: organizationId" in str(exc_info.value)

    with pytest.raises(ClientFault) as exc_info:
        cdsservices.ProcessDocument(
            mock_ctx, "123456", "WorkType", "OrganizationID", None
        )
    assert "Missing required parameter: document" in str(exc_info.value)


def test_ProcessDocument_successful_request(cdsservices):
    mock_ctx = MagicMock()
    mock_ctx.descriptor.service_class._service.return_value = MagicMock(
        document="Document", error=None
    )

    sessionId = "123456"
    workType = "WorkType"
    organizationId = "OrganizationID"
    document = [b"<xml>...</xml>"]

    response = cdsservices.ProcessDocument(
        mock_ctx, sessionId, workType, organizationId, document
    )

    assert response is not None
    assert response.Document is not None
    assert response.Error is None


def test_ProcessDocument_server_processing_error(cdsservices):
    mock_ctx = MagicMock()
    mock_ctx.descriptor.service_class._service.return_value = MagicMock(
        document="Document", error="Error"
    )

    sessionId = "123456"
    workType = "WorkType"
    organizationId = "OrganizationID"
    document = [b"<xml>...</xml>"]

    # Simulate a server processing error
    with pytest.raises(ServerFault):
        cdsservices.ProcessDocument(
            mock_ctx, sessionId, workType, organizationId, document
        )
