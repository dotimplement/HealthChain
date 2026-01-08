# ML Model Deployment as Healthcare API

Deploy any trained ML model as a production-ready FHIR endpoint with OAuth2 authentication and type-safe healthcare data handling.

## Quick Start

```bash
# 1. Install dependencies
pip install healthchain[ml] python-jose[cryptography] python-multipart

# 2. Train demo model (optional)
python ml-app/train_demo_model.py

# 3. Configure environment
cp ml-app/.env.example ml-app/.env
# Edit .env with your settings

# 4. Run the API
python ml-app/app.py
```

API available at: http://localhost:8000

## Features

| Feature | Description |
|---------|-------------|
| **FHIR Native** | Accepts FHIR Bundles, returns FHIR RiskAssessments |
| **CDS Hooks** | Real-time alerts in Epic/Cerner workflows |
| **OAuth2 JWT** | Production-ready authentication |
| **Multi-Source** | Connect to Epic, Cerner, Medplum simultaneously |
| **Type-Safe** | Pydantic models throughout |
| **Auto Docs** | OpenAPI/Swagger at `/docs` |

## API Endpoints

### Prediction Endpoints

```bash
# Predict from FHIR Bundle
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @patient_bundle.json

# Predict for patient from FHIR server
curl http://localhost:8000/predict/patient-123?source=medplum
```

### CDS Hooks

```bash
# Discovery endpoint
curl http://localhost:8000/cds/cds-services

# Patient-view hook (triggered by EHR)
curl -X POST http://localhost:8000/cds/cds-services/ml-risk-assessment \
  -H "Content-Type: application/json" \
  -d @cds_request.json
```

### Utility Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Model info
curl http://localhost:8000/model/info

# List FHIR sources
curl http://localhost:8000/sources
```

## Project Structure

```
ml-app/
├── app.py              # Main application
├── auth.py             # OAuth2 JWT authentication
├── config.py           # Configuration management
├── train_demo_model.py # Demo model training
├── .env.example        # Environment template
├── schemas/
│   └── features.yaml   # FHIR-to-features mapping
└── models/
    └── model.pkl       # Trained model (generated)
```

## Configuration

### Environment Variables

```bash
# API Settings
API_TITLE="My ML Healthcare API"
PORT=8000

# OAuth2 (optional)
OAUTH2_ENABLED=true
OAUTH2_ISSUER=https://auth.example.com
OAUTH2_AUDIENCE=my-api
OAUTH2_JWKS_URI=https://auth.example.com/.well-known/jwks.json

# FHIR Sources
MEDPLUM_CLIENT_ID=your-client-id
MEDPLUM_CLIENT_SECRET=your-secret
MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4
MEDPLUM_TOKEN_URL=https://api.medplum.com/oauth2/token
```

### Feature Schema

Define how FHIR resources map to ML features in `schemas/features.yaml`:

```yaml
features:
  heart_rate:
    fhir_resource: Observation
    code: "8867-4"
    code_system: http://loinc.org
    dtype: float64
    required: true

  age:
    fhir_resource: Patient
    field: birthDate
    transform: calculate_age
    dtype: int64
```

## Deploying Your Model

### 1. Save Model in Expected Format

```python
import joblib

model_data = {
    "model": trained_model,  # sklearn, xgboost, etc.
    "metadata": {
        "feature_names": ["heart_rate", "age", ...],
        "threshold": 0.5,
        "metrics": {"accuracy": 0.85, "roc_auc": 0.92}
    }
}
joblib.dump(model_data, "models/model.pkl")
```

### 2. Update Feature Schema

Map your model's expected features to FHIR resources in `schemas/features.yaml`.

### 3. Deploy

```bash
# Development
python app.py

# Production with gunicorn
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## OAuth2 Authentication

Enable OAuth2 for production deployments:

```bash
OAUTH2_ENABLED=true
OAUTH2_ISSUER=https://your-auth-server.com
OAUTH2_AUDIENCE=your-api-audience
OAUTH2_JWKS_URI=https://your-auth-server.com/.well-known/jwks.json
```

API calls require Bearer token:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/predict/patient-123
```

### Supported Providers

- **Auth0**: Set issuer to `https://your-tenant.auth0.com/`
- **Okta**: Set issuer to `https://your-domain.okta.com/oauth2/default`
- **Azure AD**: Set issuer to `https://login.microsoftonline.com/{tenant}/v2.0`
- **Keycloak**: Set issuer to `https://keycloak.example.com/realms/{realm}`

## FHIR Server Integration

Connect to multiple EHR systems simultaneously:

```bash
# Medplum (open-source)
MEDPLUM_CLIENT_ID=...
MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4

# Epic (production)
EPIC_CLIENT_ID=...
EPIC_CLIENT_SECRET_PATH=/path/to/private_key.pem
EPIC_BASE_URL=https://fhir.epic.com/.../api/FHIR/R4

# Cerner/Oracle Health
CERNER_CLIENT_ID=...
CERNER_BASE_URL=https://fhir-ehr.cerner.com/r4/...
```

Query any source:

```bash
curl http://localhost:8000/predict/patient-123?source=epic
curl http://localhost:8000/predict/patient-456?source=medplum
```

## CDS Hooks Integration

### Epic/Cerner Configuration

Register your CDS service in the EHR admin console:

| Setting | Value |
|---------|-------|
| Service URL | `https://your-api.com/cds/cds-services/ml-risk-assessment` |
| Hook | `patient-view` |
| Prefetch | `patient: Patient/{{context.patientId}}` |

### Testing Locally

```bash
# Start server
python app.py

# Test with sandbox client
python -c "
from healthchain.sandbox import SandboxClient
client = SandboxClient(
    url='http://localhost:8000/cds/cds-services/ml-risk-assessment',
    workflow='patient-view'
)
client.load_from_path('data/demo_patients', pattern='*.json')
responses = client.send_requests()
print(responses)
"
```

## Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ml-app .
COPY healthchain /app/healthchain

EXPOSE 8000
CMD ["gunicorn", "app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

```bash
docker build -t ml-healthcare-api .
docker run -p 8000:8000 --env-file .env ml-healthcare-api
```

## Security Considerations

- **PHI Protection**: Never log patient identifiers in production
- **OAuth2**: Enable for production deployments
- **HTTPS**: Use TLS in production (handled by reverse proxy)
- **Audit Trail**: Event system tracks all operations
- **HIPAA**: Implement BAA with cloud providers

## Troubleshooting

### Model Not Loading
```bash
# Check model path
ls -la ml-app/models/

# Train demo model if needed
python ml-app/train_demo_model.py
```

### FHIR Source Not Connecting
```bash
# Test credentials
curl -X POST https://api.medplum.com/oauth2/token \
  -d "grant_type=client_credentials" \
  -d "client_id=$MEDPLUM_CLIENT_ID" \
  -d "client_secret=$MEDPLUM_CLIENT_SECRET"
```

### OAuth2 Token Invalid
```bash
# Verify JWKS endpoint
curl https://your-auth-server.com/.well-known/jwks.json

# Check token claims
python -c "from jose import jwt; print(jwt.get_unverified_claims('$TOKEN'))"
```

## Resources

- [HealthChain Documentation](https://dotimplement.github.io/HealthChain/)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [CDS Hooks Specification](https://cds-hooks.org/)
- [SMART on FHIR](https://docs.smarthealthit.org/)
