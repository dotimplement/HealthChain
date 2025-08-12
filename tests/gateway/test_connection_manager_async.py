"""
Tests for the FHIR connection manager in the HealthChain gateway system.

This module tests centralized connection management for FHIR sources:
- Connection string parsing and validation
- Source lifecycle management
- Client pooling and retrieval
"""

import pytest
from unittest.mock import Mock, AsyncMock

from healthchain.gateway.clients.fhir.aio.connection import AsyncFHIRConnectionManager
from healthchain.gateway.api.protocols import FHIRServerInterfaceProtocol


@pytest.fixture
def connection_manager():
    """Create a connection manager for testing."""
    return AsyncFHIRConnectionManager(
        max_connections=50, max_keepalive_connections=10, keepalive_expiry=30.0
    )


@pytest.fixture
def mock_fhir_client():
    """Create a mock FHIR client using protocol."""
    client = Mock(spec=FHIRServerInterfaceProtocol)
    client.base_url = "https://test.fhir.com/R4"
    return client


@pytest.mark.asyncio
async def test_connection_manager_client_retrieval_and_default_selection(
    connection_manager, mock_fhir_client
):
    """AsyncFHIRConnectionManager retrieves clients through pooling and selects defaults correctly."""
    # Add multiple sources
    connection_manager.add_source(
        "first",
        "fhir://first.com/fhir?client_id=test&client_secret=secret&token_url=https://first.com/token",
    )
    connection_manager.add_source(
        "second",
        "fhir://second.com/fhir?client_id=test&client_secret=secret&token_url=https://second.com/token",
    )

    connection_manager.client_pool.get_client = AsyncMock(return_value=mock_fhir_client)

    # Test specific source retrieval
    client = await connection_manager.get_client("first")
    assert client == mock_fhir_client

    # Test default source selection (should use first available)
    client_default = await connection_manager.get_client()
    assert client_default == mock_fhir_client
    call_args = connection_manager.client_pool.get_client.call_args
    from urllib.parse import urlparse

    parsed_url = urlparse(call_args[0][0])
    assert (
        parsed_url.hostname == "first.com"
    )  # Should use first source's connection string
