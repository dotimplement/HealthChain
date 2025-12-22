#!/usr/bin/env python3
"""
ML Model Deployment as Healthcare API

Production-ready FHIR endpoint with OAuth2 authentication for deploying
trained ML models. Supports both real-time CDS Hooks and batch FHIR screening.

Requirements:
    pip install healthchain[ml] python-jose[cryptography] python-multipart

Run:
    python ml-app/app.py

Environment Variables:
    # OAuth2 Server Configuration (for incoming requests)
    OAUTH2_ENABLED=true
    OAUTH2_ISSUER=https://your-auth-server.com
    OAUTH2_AUDIENCE=your-api-audience
    OAUTH2_JWKS_URI=https://your-auth-server.com/.well-known/jwks.json

    # FHIR Server Configuration (for outgoing requests)
    MEDPLUM_CLIENT_ID=your-client-id
    MEDPLUM_CLIENT_SECRET=your-client-secret
    MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4
    MEDPLUM_TOKEN_URL=https://api.medplum.com/oauth2/token
"""

import logging
from pathlib import Path
from typing import Optional

import joblib
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient

from healthchain.gateway import CDSHooksService, FHIRGateway, HealthChainAPI
from healthchain.gateway.clients.fhir.base import FHIRAuthConfig
from healthchain.fhir import merge_bundles, prefetch_to_bundle
from healthchain.io import Dataset
from healthchain.models import CDSRequest, CDSResponse
from healthchain.models.responses.cdsresponse import Card
from healthchain.pipeline import Pipeline

from config import Settings, get_settings
from auth import OAuth2JWTBearer, get_current_user, UserClaims

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration paths
SCRIPT_DIR = Path(__file__).parent
MODEL_PATH = SCRIPT_DIR / "models" / "model.pkl"
SCHEMA_PATH = SCRIPT_DIR / "schemas" / "features.yaml"


class MLHealthcareAPI:
    """Production-ready ML deployment as Healthcare API."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.model = None
        self.feature_names = []
        self.threshold = 0.5
        self.pipeline = None
        self.gateway = None

        self._load_model()
        self._create_pipeline()
        self._setup_gateway()

    def _load_model(self):
        """Load the trained ML model."""
        if MODEL_PATH.exists():
            model_data = joblib.load(MODEL_PATH)
            self.model = model_data["model"]
            self.feature_names = model_data["metadata"]["feature_names"]
            self.threshold = model_data["metadata"].get("threshold", 0.5)
            logger.info(f"Loaded model with {len(self.feature_names)} features")
        else:
            logger.warning(f"Model not found at {MODEL_PATH}. Using demo mode.")
            self._create_demo_model()

    def _create_demo_model(self):
        """Create a demo model for testing without a trained model."""
        import numpy as np

        class DemoModel:
            """Demo model that returns random predictions."""
            def predict_proba(self, X):
                n_samples = len(X)
                # Generate plausible risk scores
                probs = np.random.beta(2, 5, n_samples)
                return np.column_stack([1 - probs, probs])

            def predict(self, X):
                return (self.predict_proba(X)[:, 1] > 0.5).astype(int)

        self.model = DemoModel()
        self.feature_names = [
            "heart_rate", "systolic_bp", "respiratory_rate",
            "temperature", "oxygen_saturation", "age"
        ]
        logger.info("Using demo model for testing")

    def _create_pipeline(self) -> Pipeline[Dataset]:
        """Build the ML inference pipeline."""
        pipeline = Pipeline[Dataset]()
        model = self.model
        feature_names = self.feature_names

        @pipeline.add_node
        def validate_features(dataset: Dataset) -> Dataset:
            """Ensure required features are present."""
            missing = set(feature_names) - set(dataset.data.columns)
            if missing:
                logger.warning(f"Missing features: {missing}")
            return dataset

        @pipeline.add_node
        def impute_missing(dataset: Dataset) -> Dataset:
            """Handle missing values with median imputation."""
            dataset.data = dataset.data.fillna(dataset.data.median(numeric_only=True))
            return dataset

        @pipeline.add_node
        def run_inference(dataset: Dataset) -> Dataset:
            """Run model inference."""
            # Select features that exist
            available_features = [f for f in feature_names if f in dataset.data.columns]
            if not available_features:
                dataset.metadata["probabilities"] = [0.0]
                dataset.metadata["predictions"] = [0]
                return dataset

            features = dataset.data[available_features]
            probabilities = model.predict_proba(features)[:, 1]
            predictions = (probabilities >= 0.5).astype(int)

            dataset.metadata["probabilities"] = probabilities
            dataset.metadata["predictions"] = predictions
            return dataset

        self.pipeline = pipeline
        return pipeline

    def _setup_gateway(self):
        """Setup FHIR Gateway with configured sources."""
        self.gateway = FHIRGateway()

        # Try to configure FHIR sources from environment
        for source_name in ["MEDPLUM", "EPIC", "CERNER"]:
            try:
                config = FHIRAuthConfig.from_env(source_name)
                self.gateway.add_source(source_name.lower(), config.to_connection_string())
                logger.info(f"Configured FHIR source: {source_name}")
            except Exception:
                pass  # Source not configured

    def predict_from_fhir(self, bundle) -> dict:
        """Run prediction on FHIR Bundle data."""
        dataset = Dataset.from_fhir_bundle(
            bundle,
            schema=str(SCHEMA_PATH) if SCHEMA_PATH.exists() else self._get_default_schema()
        )

        if len(dataset.data) == 0:
            return {
                "probability": 0.0,
                "prediction": 0,
                "risk_level": "unknown",
                "message": "Insufficient data for prediction"
            }

        result = self.pipeline(dataset)
        probability = float(result.metadata["probabilities"][0])
        prediction = int(result.metadata["predictions"][0])

        risk_level = self._get_risk_level(probability)

        return {
            "probability": probability,
            "prediction": prediction,
            "risk_level": risk_level,
            "features_used": list(dataset.data.columns)
        }

    def _get_risk_level(self, probability: float) -> str:
        """Map probability to risk level."""
        if probability >= 0.7:
            return "high"
        elif probability >= 0.4:
            return "moderate"
        return "low"

    def _get_default_schema(self):
        """Return default schema path from healthchain configs."""
        return str(SCRIPT_DIR.parent / "healthchain" / "configs" / "features" / "sepsis_vitals.yaml")

    def screen_patient(self, patient_id: str, source: str = "medplum") -> dict:
        """Screen a patient from FHIR server."""
        # Query patient data
        obs_bundle = self.gateway.search(
            Observation, {"patient": patient_id, "_count": "100"}, source
        )
        patient_bundle = self.gateway.search(
            Patient, {"_id": patient_id}, source
        )

        bundle = merge_bundles([patient_bundle, obs_bundle])

        if not bundle.entry:
            return {"error": "No patient data found", "patient_id": patient_id}

        result = self.predict_from_fhir(bundle)
        result["patient_id"] = patient_id
        result["source"] = source

        return result


def create_app(settings: Optional[Settings] = None) -> HealthChainAPI:
    """Create the production Healthcare API application."""
    settings = settings or get_settings()
    ml_api = MLHealthcareAPI(settings)

    # Create CDS Hooks Service
    cds = CDSHooksService()

    # OAuth2 dependency (optional based on settings)
    oauth2_scheme = OAuth2JWTBearer(settings) if settings.oauth2_enabled else None

    def get_auth_dependency():
        if settings.oauth2_enabled and oauth2_scheme:
            return Depends(oauth2_scheme)
        return None

    @cds.hook("patient-view", id="ml-risk-assessment")
    def risk_assessment_hook(request: CDSRequest) -> CDSResponse:
        """Real-time ML risk assessment triggered on patient chart open."""
        prefetch = request.prefetch or {}
        if not prefetch:
            return CDSResponse(cards=[])

        bundle = prefetch_to_bundle(prefetch)
        result = ml_api.predict_from_fhir(bundle)

        probability = result["probability"]
        risk_level = result["risk_level"]

        if risk_level in ["high", "moderate"]:
            indicator = "critical" if risk_level == "high" else "warning"
            return CDSResponse(
                cards=[
                    Card(
                        summary=f"Risk Assessment: {risk_level.upper()} ({probability:.0%})",
                        indicator=indicator,
                        detail=f"**ML Risk Assessment**\n"
                               f"- Probability: {probability:.1%}\n"
                               f"- Risk Level: {risk_level.upper()}\n"
                               f"- Features analyzed: {len(result.get('features_used', []))}",
                        title="AI-Powered Risk Assessment",
                        source={
                            "label": "HealthChain ML API",
                            "url": "https://github.com/dotimplement/HealthChain"
                        }
                    )
                ]
            )

        return CDSResponse(cards=[])

    # Create main application
    app = HealthChainAPI(
        title=settings.api_title,
        description="Production ML Model deployed as Healthcare FHIR API with OAuth2",
        version=settings.api_version,
        enable_cors=True,
        enable_events=True
    )

    # Register CDS Hooks service
    app.register_service(cds, path="/cds")

    # Register FHIR Gateway if configured
    if ml_api.gateway.sources:
        app.register_gateway(ml_api.gateway, path="/fhir")

    # Add custom ML prediction endpoints
    @app.post("/predict", tags=["ML Prediction"])
    async def predict_from_bundle(
        bundle: dict,
        user: Optional[UserClaims] = Depends(get_current_user) if settings.oauth2_enabled else None
    ):
        """
        Run ML prediction on a FHIR Bundle.

        Accepts a FHIR Bundle containing patient data and returns risk assessment.
        """
        from fhir.resources.bundle import Bundle
        fhir_bundle = Bundle(**bundle)
        result = ml_api.predict_from_fhir(fhir_bundle)

        if user:
            result["requested_by"] = user.sub

        return result

    @app.get("/predict/{patient_id}", tags=["ML Prediction"])
    async def predict_for_patient(
        patient_id: str,
        source: str = "medplum",
        user: Optional[UserClaims] = Depends(get_current_user) if settings.oauth2_enabled else None
    ):
        """
        Screen a patient from configured FHIR source.

        Queries patient data from the specified FHIR server and runs prediction.
        """
        if not ml_api.gateway.sources:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No FHIR sources configured"
            )

        if source not in ml_api.gateway.sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source '{source}' not configured. Available: {list(ml_api.gateway.sources.keys())}"
            )

        result = ml_api.screen_patient(patient_id, source)

        if user:
            result["requested_by"] = user.sub

        return result

    @app.get("/model/info", tags=["ML Model"])
    async def model_info():
        """Get information about the deployed ML model."""
        return {
            "model_loaded": ml_api.model is not None,
            "feature_count": len(ml_api.feature_names),
            "features": ml_api.feature_names,
            "threshold": ml_api.threshold,
            "demo_mode": not MODEL_PATH.exists()
        }

    @app.get("/sources", tags=["FHIR Sources"])
    async def list_sources():
        """List configured FHIR data sources."""
        return {
            "sources": list(ml_api.gateway.sources.keys()) if ml_api.gateway else [],
            "configured": bool(ml_api.gateway and ml_api.gateway.sources)
        }

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    print("\n" + "="*60)
    print("ML Healthcare API - Starting Server")
    print("="*60)
    print(f"Title: {settings.api_title}")
    print(f"OAuth2 Enabled: {settings.oauth2_enabled}")
    print(f"Demo Mode: {not MODEL_PATH.exists()}")
    print("="*60 + "\n")

    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
