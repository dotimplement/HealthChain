"""Basic tests for the diabetes risk app"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import DiabetesRiskApp


@pytest.fixture
def test_client():
    """Create test client"""
    app = DiabetesRiskApp()
    return TestClient(app.app)


def test_cds_discovery(test_client):
    """Test CDS Hooks discovery endpoint"""
    response = test_client.get("/cds/cds-discovery")
    assert response.status_code == 200

    services = response.json()["services"]
    service_ids = [s["id"] for s in services]
    assert "diabetes-risk-assessment" in service_ids

    print(f"\n✓ Discovered {len(services)} CDS services")


def test_health_check(test_client):
    """Test API health"""
    response = test_client.get("/")
    assert response.status_code in [200, 404]  # Either welcome or not found is ok


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
