from typing import List
import pickle
from pathlib import Path

from healthchain.gateway import HealthChainAPI, CDSHooksService, FHIRGateway
from healthchain.io.containers import Dataset
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdsresponse import CDSResponse, Card, IndicatorEnum, Source, Suggestion, Action, ActionTypeEnum
from healthchain.fhir.readers import prefetch_to_bundle
from healthchain.fhir.resourcehelpers import create_risk_assessment_from_prediction
from healthchain.fhir.bundlehelpers import add_resource
from fhir.resources.bundle import Bundle

import yaml
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


class DiabetesRiskApp:
    """
    Diabetes Risk Monitoring System

    Integrates with multiple FHIR sources, performs ML-based risk assessment,
    and delivers real-time alerts via CDS Hooks.
    """

    def __init__(self, config_path: str = "config/fhir_servers.yaml"):
        # Initialize HealthChain API
        self.app = HealthChainAPI()

        # Load configurations
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # Initialize FHIR Gateway for multi-source data
        self.fhir_gateway = FHIRGateway()
        self._setup_fhir_sources()

        # Initialize CDS Hooks Service
        self.cds_service = CDSHooksService()
        self._setup_cds_hooks()
        
        # Register service with API (needed for testing)
        self.app.register_service(self.cds_service)

        # Load ML model
        self.model = self._load_model()

        # Load feature schema
        with open("config/feature_schema.yaml") as f:
            self.feature_schema = yaml.safe_load(f)

    def _setup_fhir_sources(self):
        """Configure multiple FHIR sources"""
        for source_name, source_config in self.config.get("sources", {}).items():
            # Build connection string in format: fhir://hostname/path?params
            base_url = source_config["base_url"]
            # Parse URL and build connection string
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            
            # Build connection string
            if source_config.get("auth"):
                # With auth
                auth = source_config["auth"]
                params = []
                if auth.get("client_id"):
                    params.append(f"client_id={auth['client_id']}")
                if auth.get("client_secret"):
                    params.append(f"client_secret={auth['client_secret']}")
                if auth.get("token_url"):
                    params.append(f"token_url={auth['token_url']}")
                query_string = "&".join(params)
                connection_string = f"fhir://{parsed.netloc}{parsed.path}?{query_string}"
            else:
                # Without auth (e.g., Medplum)
                connection_string = f"fhir://{parsed.netloc}{parsed.path}"
            
            try:
                self.fhir_gateway.add_source(name=source_name, connection_string=connection_string)
            except Exception as e:
                print(f"Warning: Could not add FHIR source {source_name}: {e}")

    def _setup_cds_hooks(self):
        """Register CDS Hooks services"""

        @self.cds_service.hook(
            hook_type="patient-view",
            id="diabetes-risk-assessment",
            title="Diabetes Risk Assessment",
            description="Assesses diabetes risk based on patient data"
        )
        def diabetes_risk_hook(data: CDSRequest) -> CDSResponse:
            """
            CDS Hook handler for real-time diabetes risk assessment

            Triggered when a clinician opens a patient's chart
            """
            return self._assess_risk(data)

        @self.cds_service.hook(
            hook_type="order-select",
            id="diabetes-screening-recommendation",
            title="Diabetes Screening Recommendation",
            description="Recommends diabetes screening for high-risk patients"
        )
        def screening_recommendation_hook(data: CDSRequest) -> CDSResponse:
            """
            Recommends HbA1c screening for patients without recent tests
            """
            return self._recommend_screening(data)

    def _load_model(self) -> RandomForestClassifier:
        """Load trained ML model"""
        # Try multiple possible paths
        possible_paths = [
            Path("diabetes_risk_app/models/diabetes_model.pkl"),
            Path("models/diabetes_model.pkl"),
            Path(__file__).parent / "diabetes_risk_app" / "models" / "diabetes_model.pkl",
        ]
        
        for model_path in possible_paths:
            if model_path.exists():
                with open(model_path, "rb") as f:
                    return pickle.load(f)
        
        # For demo purposes, train a simple model
        print("⚠️  No trained model found, using demo model")
        return self._train_demo_model()

    def _train_demo_model(self) -> RandomForestClassifier:
        """Train a demo model (replace with real training data)"""
        # Synthetic training data
        X = pd.DataFrame({
            'age': [45, 55, 35, 60, 50, 40, 65, 30],
            'bmi': [28, 32, 24, 35, 29, 26, 33, 22],
            'glucose_fasting': [100, 126, 90, 140, 110, 95, 135, 85],
            'systolic_bp': [130, 145, 120, 150, 135, 125, 148, 115],
            'diastolic_bp': [85, 92, 78, 95, 88, 80, 94, 75],
        })
        y = [0, 1, 0, 1, 1, 0, 1, 0]  # 0=low risk, 1=high risk

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)

        # Save model
        model_dir = Path(__file__).parent / "diabetes_risk_app" / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        with open(model_dir / "diabetes_model.pkl", "wb") as f:
            pickle.dump(model, f)

        return model

    def _assess_risk(self, cds_request: CDSRequest) -> CDSResponse:
        """
        Main risk assessment logic

        1. Extract patient data from CDS request
        2. Convert to ML features using Dataset container
        3. Run ML prediction
        4. Create CDS card with risk level
        5. Generate FHIR RiskAssessment resource
        """
        try:
            # Extract FHIR bundle from CDS request prefetch
            if not cds_request.prefetch:
                return CDSResponse(cards=[
                    Card(
                        summary="No patient data provided",
                        indicator=IndicatorEnum.info,
                        source=Source(label="Diabetes Risk Model")
                    )
                ])

            # Convert prefetch to bundle format
            bundle_dict = prefetch_to_bundle(cds_request.prefetch)
            bundle = Bundle(**bundle_dict)

            # Convert FHIR to ML features
            dataset = Dataset.from_fhir_bundle(
                bundle,
                schema=self.feature_schema
            )

            if dataset.data.empty:
                return CDSResponse(cards=[
                    Card(
                        summary="Insufficient data for diabetes risk assessment",
                        indicator=IndicatorEnum.info,
                        source=Source(label="Diabetes Risk Model")
                    )
                ])

            # Prepare features for model
            feature_cols = ['age', 'bmi', 'glucose_fasting', 'systolic_bp', 'diastolic_bp']
            # Only use columns that exist
            available_cols = [col for col in feature_cols if col in dataset.data.columns]
            if not available_cols:
                return CDSResponse(cards=[
                    Card(
                        summary="Required features not found in patient data",
                        indicator=IndicatorEnum.info,
                        source=Source(label="Diabetes Risk Model")
                    )
                ])

            X = dataset.data[available_cols].fillna(dataset.data[available_cols].median())

            # Predict risk
            risk_prob = self.model.predict_proba(X)[0][1]  # Probability of high risk
            risk_level = "High" if risk_prob > 0.7 else "Moderate" if risk_prob > 0.4 else "Low"

            # Determine card indicator
            if risk_level == "High":
                indicator = IndicatorEnum.warning
                summary = f"⚠️ High Diabetes Risk Detected ({risk_prob:.1%})"
            elif risk_level == "Moderate":
                indicator = IndicatorEnum.info
                summary = f"Moderate Diabetes Risk ({risk_prob:.1%})"
            else:
                indicator = IndicatorEnum.success
                summary = f"Low Diabetes Risk ({risk_prob:.1%})"

            # Create CDS card
            card = Card(
                summary=summary,
                indicator=indicator,
                source=Source(label="Diabetes Risk ML Model"),
                detail=self._create_risk_detail(X.iloc[0], risk_prob),
                suggestions=self._create_suggestions(risk_level)
            )

            # Create FHIR RiskAssessment resource
            patient_id = None
            if cds_request.prefetch and "patient" in cds_request.prefetch:
                patient_resource = cds_request.prefetch["patient"]
                if isinstance(patient_resource, dict) and "id" in patient_resource:
                    patient_id = f"Patient/{patient_resource['id']}"
                elif hasattr(patient_resource, "id"):
                    patient_id = f"Patient/{patient_resource.id}"

            if patient_id:
                risk_assessment = create_risk_assessment_from_prediction(
                    patient_id=patient_id,
                    prediction=risk_prob,
                    outcome_code="44054006",  # SNOMED CT: Diabetes mellitus type 2
                    outcome_display="Type 2 Diabetes",
                    model_name="DiabetesRiskModel",
                    model_version="1.0"
                )

                # Add to bundle (could be written back to FHIR server)
                add_resource(bundle, risk_assessment)

            return CDSResponse(cards=[card])

        except Exception as e:
            print(f"Error in risk assessment: {e}")
            import traceback
            traceback.print_exc()
            return CDSResponse(cards=[
                Card(
                    summary="Error performing diabetes risk assessment",
                    indicator=IndicatorEnum.info,
                    source=Source(label="Diabetes Risk Model"),
                    detail=str(e)
                )
            ])

    def _create_risk_detail(self, patient_features: pd.Series, risk_prob: float) -> str:
        """Create detailed risk explanation"""
        details = f"""
**Risk Score**: {risk_prob:.1%}

**Contributing Factors**:
"""
        for col in patient_features.index:
            if col in ['age', 'bmi', 'glucose_fasting', 'systolic_bp', 'diastolic_bp']:
                if col == 'age':
                    details += f"- Age: {patient_features[col]:.0f} years\n"
                elif col == 'bmi':
                    details += f"- BMI: {patient_features[col]:.1f}\n"
                elif col == 'glucose_fasting':
                    details += f"- Fasting Glucose: {patient_features[col]:.0f} mg/dL\n"
                elif col == 'systolic_bp':
                    details += f"- Blood Pressure: {patient_features[col]:.0f}/"
                elif col == 'diastolic_bp':
                    details += f"{patient_features[col]:.0f} mmHg\n"

        details += "\n**Interpretation**:\n"
        if risk_prob > 0.7:
            details += "Patient shows multiple risk factors for Type 2 Diabetes. Consider lifestyle intervention and close monitoring."
        elif risk_prob > 0.4:
            details += "Patient has moderate risk. Recommend lifestyle modifications and periodic screening."
        else:
            details += "Patient has low current risk. Continue routine preventive care."

        return details

    def _create_suggestions(self, risk_level: str) -> List[Suggestion]:
        """Create actionable suggestions based on risk level"""
        if risk_level == "High":
            return [
                Suggestion(
                    label="Order HbA1c test",
                    actions=[
                        Action(
                            type=ActionTypeEnum.create,
                            description="Order HbA1c laboratory test",
                            resource={
                                "resourceType": "ServiceRequest",
                                "status": "draft",
                                "intent": "order",
                                "code": {
                                    "coding": [{
                                        "system": "http://loinc.org",
                                        "code": "4548-4",
                                        "display": "Hemoglobin A1c"
                                    }]
                                }
                            }
                        )
                    ]
                ),
                Suggestion(
                    label="Refer to endocrinology",
                    actions=[
                        Action(
                            type=ActionTypeEnum.create,
                            description="Create referral to endocrinology"
                        )
                    ]
                )
            ]
        elif risk_level == "Moderate":
            return [
                Suggestion(
                    label="Schedule follow-up in 3 months",
                    actions=[
                        Action(
                            type=ActionTypeEnum.create,
                            description="Schedule follow-up appointment"
                        )
                    ]
                )
            ]
        else:
            return []

    def _recommend_screening(self, cds_request: CDSRequest) -> CDSResponse:
        """Recommend screening for patients without recent HbA1c"""
        # Implementation similar to _assess_risk
        # Check for recent HbA1c observations
        # Recommend screening if none found in last 6 months
        return CDSResponse(cards=[])

    def batch_screening(self, patient_ids: List[str]) -> pd.DataFrame:
        """
        Run batch screening for a list of patients

        Args:
            patient_ids: List of patient IDs to screen

        Returns:
            DataFrame with patient IDs and risk scores
        """
        results = []

        for patient_id in patient_ids:
            try:
                # Fetch patient bundle from FHIR
                bundle = self.fhir_gateway.get_patient_bundle(patient_id)

                # Convert to ML features
                dataset = Dataset.from_fhir_bundle(
                    bundle,
                    schema=self.feature_schema
                )

                if dataset.data.empty:
                    continue

                # Predict risk
                feature_cols = ['age', 'bmi', 'glucose_fasting', 'systolic_bp', 'diastolic_bp']
                available_cols = [col for col in feature_cols if col in dataset.data.columns]
                X = dataset.data[available_cols].fillna(dataset.data[available_cols].median())
                risk_prob = self.model.predict_proba(X)[0][1]

                results.append({
                    'patient_id': patient_id,
                    'risk_probability': risk_prob,
                    'risk_level': 'High' if risk_prob > 0.7 else 'Moderate' if risk_prob > 0.4 else 'Low'
                })

            except Exception as e:
                print(f"Error screening patient {patient_id}: {e}")
                continue

        return pd.DataFrame(results)

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the application server"""
        # Service already registered in __init__
        # Start FastAPI server
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)


# Entry point
if __name__ == "__main__":
    app = DiabetesRiskApp()
    print("\n✓ Starting Diabetes Risk Monitoring System...")
    print("✓ Visit http://localhost:8000/cds/cds-discovery to see available services")
    print("✓ API docs available at http://localhost:8000/docs\n")
    app.run()
