"""
Integration tests for gateway components working together.

Tests the complete flow: Gateway -> ConnectionManager -> Client -> HTTP
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle

from healthchain.gateway.fhir import FHIRGateway, AsyncFHIRGateway


def test_sync_gateway_full_integration_flow(standard_connection_string):
    """Complete sync flow: Gateway -> ConnectionManager -> Client -> HTTP."""

    # Mock the client creation at the connection manager level
    with patch(
        "healthchain.gateway.clients.fhir.sync.connection.FHIRConnectionManager.get_client"
    ) as mock_get_client:
        # Create a mock client with expected methods
        mock_client = Mock()
        mock_client.read.return_value = Patient(id="test-patient-123", active=True)
        mock_get_client.return_value = mock_client

        # Create gateway and add source (this will be mocked out)
        gateway = FHIRGateway(use_events=False)
        gateway.add_source("test_source", standard_connection_string)

        # Execute operation - this should flow through all layers
        result = gateway.read(Patient, "test-patient-123", "test_source")

        # Verify the complete chain worked
        assert isinstance(result, Patient)
        assert result.id == "test-patient-123"
        assert result.active is True

        # Verify client method was called correctly
        mock_client.read.assert_called_once_with(Patient, "test-patient-123")


@pytest.mark.asyncio
async def test_async_gateway_full_integration_flow(standard_connection_string):
    """Complete async flow: Gateway -> ConnectionManager -> Client -> HTTP."""

    # Mock the client creation at the async connection manager level
    with patch(
        "healthchain.gateway.clients.fhir.aio.connection.AsyncFHIRConnectionManager.get_client"
    ) as mock_get_client:
        # Create a mock async client with async methods
        mock_client = Mock()
        mock_client.read = AsyncMock(
            return_value=Patient(id="test-patient-123", active=True)
        )
        mock_get_client.return_value = mock_client

        # Mock the connection manager close to avoid async context manager issues
        with patch(
            "healthchain.gateway.clients.fhir.aio.connection.AsyncFHIRConnectionManager.close"
        ):
            # Create async gateway and add source
            async with AsyncFHIRGateway(use_events=False) as gateway:
                gateway.add_source("test_source", standard_connection_string)

                # Execute operation - this should flow through all async layers
                result = await gateway.read(Patient, "test-patient-123", "test_source")

                # Verify the complete chain worked
                assert isinstance(result, Patient)
                assert result.id == "test-patient-123"
                assert result.active is True

                # Verify client method was called correctly
                mock_client.read.assert_called_once_with(Patient, "test-patient-123")


def test_sync_gateway_error_propagation_chain(standard_connection_string):
    """HTTP errors properly propagate through: Client -> Gateway -> User."""
    import httpx

    # Mock the client to raise timeout error
    with patch(
        "healthchain.gateway.clients.fhir.sync.connection.FHIRConnectionManager.get_client"
    ) as mock_get_client:
        mock_client = Mock()
        mock_client.read.side_effect = httpx.ConnectTimeout("Connection timed out")
        mock_get_client.return_value = mock_client

        # Create gateway
        gateway = FHIRGateway(use_events=False)
        gateway.add_source("test_source", standard_connection_string)

        # Execute operation and expect proper error propagation
        with pytest.raises(Exception) as exc_info:
            gateway.read(Patient, "test-patient-123", "test_source")

        # Verify error chain includes original timeout
        assert (
            "timed out" in str(exc_info.value).lower()
            or "timeout" in str(exc_info.value).lower()
        )


def test_sync_gateway_multi_source_integration():
    """Gateway handles multiple sources correctly in integration."""
    connection_string1 = "fhir://source1.fhir.org/R4?client_id=client1&client_secret=secret1&token_url=https://source1.fhir.org/token"
    connection_string2 = "fhir://source2.fhir.org/R4?client_id=client2&client_secret=secret2&token_url=https://source2.fhir.org/token"

    # Mock the connection manager to return different clients for different sources
    with patch(
        "healthchain.gateway.clients.fhir.sync.connection.FHIRConnectionManager.get_client"
    ) as mock_get_client:
        # Create different mock clients for different sources
        mock_client1 = Mock()
        mock_client1.read.return_value = Patient(
            id="123", active=True, name=[{"family": "Source1Patient"}]
        )

        mock_client2 = Mock()
        mock_client2.read.return_value = Patient(
            id="456", active=False, name=[{"family": "Source2Patient"}]
        )

        # Return appropriate client based on call order
        mock_get_client.side_effect = [mock_client1, mock_client2]

        # Create gateway with multiple sources
        gateway = FHIRGateway(use_events=False)
        gateway.add_source("source1", connection_string1)
        gateway.add_source("source2", connection_string2)

        # Test reading from specific sources
        patient1 = gateway.read(Patient, "123", "source1")
        patient2 = gateway.read(Patient, "456", "source2")

        # Verify correct patients from correct sources
        assert patient1.name[0].family == "Source1Patient"
        assert patient2.name[0].family == "Source2Patient"

        # Verify correct calls were made
        assert mock_get_client.call_count == 2
        mock_client1.read.assert_called_once_with(Patient, "123")
        mock_client2.read.assert_called_once_with(Patient, "456")


def test_sync_gateway_transaction_bundle_integration(
    standard_connection_string, sample_bundle
):
    """Gateway properly handles transaction bundles through the full stack."""

    # Mock the client to return transaction response
    with patch(
        "healthchain.gateway.clients.fhir.sync.connection.FHIRConnectionManager.get_client"
    ) as mock_get_client:
        mock_client = Mock()
        mock_client.transaction.return_value = Bundle(
            type="transaction-response",
            entry=[
                {
                    "response": {"status": "200 OK"},
                    "resource": {
                        "resourceType": "Patient",
                        "id": "123",
                        "active": True,
                    },
                }
            ],
        )
        mock_get_client.return_value = mock_client

        # Create gateway and execute transaction
        gateway = FHIRGateway(use_events=False)
        gateway.add_source("test_source", standard_connection_string)

        result = gateway.transaction(sample_bundle, "test_source")

        # Verify transaction bundle was processed
        assert isinstance(result, Bundle)
        assert result.type == "transaction-response"

        # Verify transaction method was called with the bundle
        mock_client.transaction.assert_called_once_with(sample_bundle)
