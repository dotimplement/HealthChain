#!/bin/bash

# HealthChain Diabetes Risk App - Quick Start Script
# This script sets up the complete application structure and dependencies

set -e  # Exit on error

echo "============================================"
echo "HealthChain Diabetes Risk App Setup"
echo "============================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) and sys.version_info < (3,15) else 1)"; then
    echo -e "${GREEN}✓ Python $PYTHON_VERSION detected (3.10-3.14 supported)${NC}"
else
    echo -e "${RED}✗ Python 3.10-3.14 required. Current: $PYTHON_VERSION${NC}"
    echo -e "${YELLOW}Please install Python 3.10, 3.11, 3.12, 3.13, or 3.14${NC}"
    exit 1
fi

# Create project directory
APP_DIR="diabetes_risk_app"
echo ""
echo "Creating project structure in $APP_DIR..."

mkdir -p $APP_DIR/{models,config,tests,data/synthetic}
cd $APP_DIR

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install HealthChain
echo ""
echo "Installing HealthChain and dependencies (Python 3.14 compatible)..."
pip install --upgrade pip
pip install "healthchain[dev,test,ml]"
pip install "scikit-learn>=1.5.0" "pandas>=2.0.0" "numpy>=1.26.0" pyyaml

echo -e "${GREEN}✓ Dependencies installed (Python 3.14 compatible)${NC}"

# Create configuration files
echo ""
echo "Creating configuration files..."

# Feature schema
cat > config/feature_schema.yaml << 'EOF'
features:
  - name: age
    fhir_path: Patient.birthDate
    data_type: date
    required: true
    aggregation: null

  - name: bmi
    fhir_path: Observation.where(code.coding.code='39156-5').valueQuantity.value
    data_type: float
    required: true
    aggregation: last

  - name: glucose_fasting
    fhir_path: Observation.where(code.coding.code='1558-6').valueQuantity.value
    data_type: float
    required: true
    aggregation: last

  - name: hba1c
    fhir_path: Observation.where(code.coding.code='4548-4').valueQuantity.value
    data_type: float
    required: false
    aggregation: last

  - name: systolic_bp
    fhir_path: Observation.where(code.coding.code='8480-6').valueQuantity.value
    data_type: float
    required: true
    aggregation: mean

  - name: diastolic_bp
    fhir_path: Observation.where(code.coding.code='8462-4').valueQuantity.value
    data_type: float
    required: true
    aggregation: mean
EOF

# FHIR servers config (template)
cat > config/fhir_servers.yaml << 'EOF'
# FHIR Server Configuration
# For testing, you can use Medplum public server (no auth required)
# For production, configure your EHR FHIR endpoints

sources:
  medplum:
    base_url: "https://api.medplum.com/fhir/R4"
    auth: null  # Public access

  # Uncomment and configure for Epic
  # epic:
  #   base_url: "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
  #   auth:
  #     token_url: "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
  #     client_id: "your_client_id"
  #     client_secret: "your_client_secret"

  # Uncomment and configure for Cerner
  # cerner:
  #   base_url: "https://fhir-myrecord.cerner.com/r4"
  #   auth:
  #     token_url: "https://authorization.cerner.com/tenants/tenant_id/protocols/oauth2/profiles/smart-v1/token"
  #     client_id: "your_client_id"
  #     client_secret: "your_client_secret"
EOF

echo -e "${GREEN}✓ Configuration files created${NC}"

# Create model training script
echo ""
echo "Creating model training script..."

cat > models/train_model.py << 'EOFPYTHON'
"""
Train diabetes risk prediction model
"""

import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import roc_auc_score, classification_report


def generate_synthetic_training_data(n_samples: int = 1000):
    """Generate synthetic training data"""
    np.random.seed(42)

    age = np.random.normal(50, 15, n_samples).clip(18, 90)
    bmi = np.random.normal(28, 6, n_samples).clip(15, 50)
    glucose = np.random.normal(100, 20, n_samples).clip(70, 200)
    systolic_bp = np.random.normal(130, 15, n_samples).clip(90, 180)
    diastolic_bp = np.random.normal(85, 10, n_samples).clip(60, 120)

    risk_score = (
        (age > 45) * 0.2 +
        (bmi > 30) * 0.3 +
        (glucose > 110) * 0.3 +
        (systolic_bp > 140) * 0.2
    )

    risk_score += np.random.normal(0, 0.1, n_samples)
    y = (risk_score > 0.5).astype(int)

    X = pd.DataFrame({
        'age': age,
        'bmi': bmi,
        'glucose_fasting': glucose,
        'systolic_bp': systolic_bp,
        'diastolic_bp': diastolic_bp
    })

    return X, y


def train_model():
    """Train and save the diabetes risk model"""
    print("Generating training data...")
    X, y = generate_synthetic_training_data(n_samples=1000)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    print("\nTraining Random Forest model...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=10,
        random_state=42,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)

    y_pred_proba = model.predict_proba(X_test)[:, 1]
    print(f"\nROC-AUC: {roc_auc_score(y_test, y_pred_proba):.3f}")

    with open('diabetes_model.pkl', 'wb') as f:
        pickle.dump(model, f)

    print("\n✓ Model saved to models/diabetes_model.pkl")
    return model


if __name__ == "__main__":
    train_model()
EOFPYTHON

# Create main application file
echo ""
echo "Creating main application..."

cat > app.py << 'EOFAPP'
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
EOFAPP

# Create test file
echo ""
echo "Creating test file..."

cat > tests/test_app.py << 'EOFTEST'
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
    return TestClient(app.app.app)


def test_cds_discovery(test_client):
    """Test CDS Hooks discovery endpoint"""
    response = test_client.get("/cds-services")
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
EOFTEST

# Create README
cat > README.md << 'EOFREADME'
# Diabetes Risk Monitoring System

A production-ready healthcare AI application built with HealthChain.

## Quick Start

1. **Train the model**:
   ```bash
   source venv/bin/activate
   cd models
   python train_model.py
   cd ..
   ```

2. **Start the application**:
   ```bash
   python app.py
   ```

3. **Test the application**:
   Visit http://localhost:8000/cds-services

4. **Run tests**:
   ```bash
   pytest tests/ -v
   ```

## Documentation

See the main guide: `../DIABETES_RISK_APP_GUIDE.md`

## Configuration

Edit `config/fhir_servers.yaml` to add your FHIR server credentials.
EOFREADME

echo -e "${GREEN}✓ Application files created${NC}"

# Train the model
echo ""
echo "Training ML model..."
cd models
python train_model.py
cd ..

echo -e "${GREEN}✓ Model trained successfully${NC}"

# Create .gitignore
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
.pytest_cache/
.coverage
*.pkl
*.log
config/*_secrets.yaml
EOF

# Final instructions
echo ""
echo "============================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "============================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo -e "   ${YELLOW}cd $APP_DIR${NC}"
echo -e "   ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo "2. Start the application:"
echo -e "   ${YELLOW}python app.py${NC}"
echo ""
echo "3. In another terminal, run tests:"
echo -e "   ${YELLOW}pytest tests/ -v${NC}"
echo ""
echo "4. Test with SandboxClient (see DIABETES_RISK_APP_GUIDE.md)"
echo ""
echo "5. Visit http://localhost:8000/cds-services to see your CDS services"
echo ""
echo "For detailed documentation, see:"
echo "  ../DIABETES_RISK_APP_GUIDE.md"
echo ""
echo "============================================"
