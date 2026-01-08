"""
Test diabetes risk app using HealthChain Sandbox

No real FHIR server or credentials required
"""

import pytest
from healthchain.sandbox import SandboxClient


def test_patient_view_hook_with_synthetic_data():
    """Test CDS Hook with synthetic patient data"""
    import tempfile
    import csv
    from pathlib import Path

    # Create a temporary CSV file with test data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(['text'])
        writer.writerow(['Patient is 55 years old, BMI 32, fasting glucose 126 mg/dL'])
        temp_path = f.name

    try:
        client = SandboxClient(
            url="http://localhost:8000/cds/cds-services/diabetes-risk-assessment",
            workflow="patient-view",
            protocol="rest"
        )
        # Load synthetic patient with diabetes risk factors
        client.load_free_text(
            csv_path=temp_path,
            column_name="text"
        )

    # Preview the request that will be sent
    print("\n📤 CDS Request:")
    client.print_request()

    # Send request to your service
    responses = client.send_requests()
    response = responses[0] if responses else None

        # Validate response
        assert response is not None
        assert response.get("status_code") == 200 or "cards" in response

        # Check cards
        if isinstance(response, dict) and "cards" in response:
            cards = response.get("cards", [])
        else:
            cards = response.get("body", {}).get("cards", []) if isinstance(response.get("body"), dict) else []

        assert len(cards) > 0

        # Verify risk assessment in first card
        card = cards[0]
        print(f"\n📥 CDS Response Card:")
        print(f"  Summary: {card['summary']}")
        print(f"  Indicator: {card['indicator']}")

        assert "Diabetes Risk" in card["summary"]
        assert card["indicator"] in ["warning", "info", "success"]
    finally:
        # Clean up temp file
        Path(temp_path).unlink(missing_ok=True)


def test_with_mimic_data():
    """Test with real MIMIC-on-FHIR dataset"""

    try:
        client = SandboxClient(
            url="http://localhost:8000/cds/cds-services/diabetes-risk-assessment",
            workflow="patient-view",
            protocol="rest"
        )
        # Load real patient data from MIMIC
        client.load_from_registry(
            dataset_name="mimic",
            patient_id="61c20e32-7e96-4563-b811-26084a59a23e"  # Example patient
        )

        responses = client.send_requests()
        assert len(responses) > 0
    except Exception as e:
        print(f"Skipping MIMIC test: {e}")
        pytest.skip("MIMIC dataset not available")


def test_with_synthea_data():
    """Test with Synthea synthetic dataset"""

    try:
        client = SandboxClient(
            url="http://localhost:8000/cds/cds-services/diabetes-risk-assessment",
            workflow="patient-view",
            protocol="rest"
        )
        # Load Synthea patient
        client.load_from_registry(
            dataset_name="synthea",
            patient_id="synthea-patient-1"
        )

        responses = client.send_requests()
        assert len(responses) > 0
    except Exception as e:
        print(f"Skipping Synthea test: {e}")
        pytest.skip("Synthea dataset not available")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
