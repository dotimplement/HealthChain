"""
End-to-end integration tests

Tests complete workflow from FHIR → ML → CDS response
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app import DiabetesRiskApp


@pytest.fixture
def test_client():
    """Create test client for the app"""
    app = DiabetesRiskApp()
    return TestClient(app.app)


def test_cds_discovery(test_client):
    """Test CDS Hooks discovery endpoint"""
    response = test_client.get("/cds/cds-discovery")

    assert response.status_code == 200
    data = response.json()
    
    # Check our services are registered
    services = data.get("services", [])
    service_ids = [s.get("id") for s in services]
    assert "diabetes-risk-assessment" in service_ids

    print(f"\n✅ Discovered {len(services)} CDS services")


def test_cds_hook_endpoint(test_client):
    """Test CDS Hook endpoint with minimal data"""

    # Minimal CDS request
    cds_request = {
        "hook": "patient-view",
        "hookInstance": "test-123",
        "context": {
            "userId": "Practitioner/example",
            "patientId": "Patient/example"
        },
        "prefetch": {
            "patient": {
                "resourceType": "Patient",
                "id": "example",
                "birthDate": "1970-01-01"
            },
            "conditions": {
                "resourceType": "Bundle",
                "entry": []
            },
            "observations": {
                "resourceType": "Bundle",
                "entry": []
            }
        }
    }

    response = test_client.post(
        "/cds/cds-services/diabetes-risk-assessment",
        json=cds_request
    )

    assert response.status_code == 200

    # Even with minimal data, should return valid CDS response
    data = response.json()
    assert "cards" in data


def test_model_prediction_accuracy():
    """Test ML model predictions"""
    from app import DiabetesRiskApp
    import pandas as pd

    app = DiabetesRiskApp()

    # High risk patient
    high_risk_features = pd.DataFrame([{
        'age': 65,
        'bmi': 35,
        'glucose_fasting': 140,
        'systolic_bp': 150,
        'diastolic_bp': 95
    }])

    risk_prob = app.model.predict_proba(high_risk_features)[0][1]
    assert risk_prob > 0.5, "Should predict high risk"

    # Low risk patient
    low_risk_features = pd.DataFrame([{
        'age': 30,
        'bmi': 22,
        'glucose_fasting': 85,
        'systolic_bp': 115,
        'diastolic_bp': 75
    }])

    risk_prob = app.model.predict_proba(low_risk_features)[0][1]
    assert risk_prob < 0.5, "Should predict low risk"

    print("\n✅ Model predictions validated")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

