from typing import List
import pickle
from pathlib import Path

from healthchain import HealthChainAPI
from healthchain.gateway import CDSHooksGateway
from healthchain.models import CDSRequest, CDSResponse, Card, Indicator

import yaml
import pandas as pd


class DiabetesRiskApp:
    """Diabetes Risk Monitoring System"""

    def __init__(self):
        self.app = HealthChainAPI()
        self.cds_gateway = CDSHooksGateway()
        self._setup_cds_hooks()
        self.model = self._load_model()

    def _setup_cds_hooks(self):
        """Register CDS Hooks services"""

        @self.cds_gateway.service(
            hook="patient-view",
            title="Diabetes Risk Assessment",
            description="Assesses diabetes risk based on patient data",
            id="diabetes-risk-assessment"
        )
        def diabetes_risk_hook(data: CDSRequest) -> CDSResponse:
            return self._assess_risk(data)

    def _load_model(self):
        """Load trained ML model"""
        model_path = Path("models/diabetes_model.pkl")
        if model_path.exists():
            with open(model_path, "rb") as f:
                return pickle.load(f)
        else:
            print("⚠️  No trained model found. Run: python models/train_model.py")
            return None

    def _assess_risk(self, cds_request: CDSRequest) -> CDSResponse:
        """Main risk assessment logic"""
        if self.model is None:
            return CDSResponse(cards=[
                Card(
                    summary="Model not loaded. Please train the model first.",
                    indicator=Indicator.info,
                    source={"label": "Diabetes Risk Model"}
                )
            ])

        # Simplified demo response
        card = Card(
            summary="Diabetes Risk Assessment Demo",
            indicator=Indicator.info,
            source={"label": "Diabetes Risk Model"},
            detail="This is a demo response. Integrate with real FHIR data for production use."
        )

        return CDSResponse(cards=[card])

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the application server"""
        self.app.mount_gateway(self.cds_gateway)

        import uvicorn
        uvicorn.run(self.app.app, host=host, port=port)


if __name__ == "__main__":
    app = DiabetesRiskApp()
    print("\n✓ Starting Diabetes Risk Monitoring System...")
    print("✓ Visit http://localhost:8000/cds-services to see available services")
    print("✓ API docs available at http://localhost:8000/docs\n")
    app.run()
