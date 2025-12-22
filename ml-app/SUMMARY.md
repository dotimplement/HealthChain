# ML Healthcare API - Business & Technical Summary

## Executive Summary

This solution enables healthcare organizations to deploy ML models as production-ready FHIR APIs with enterprise-grade security. It transforms trained models into real-time clinical decision support tools integrated directly into EHR workflows.

---

## Business Value

### Problem Solved

Healthcare AI faces a critical deployment gap:

| Challenge | Impact | Our Solution |
|-----------|--------|--------------|
| EHR Integration Complexity | 6-12 months to integrate with each system | Native FHIR/CDS Hooks support (days) |
| Security & Compliance | Custom auth for each deployment | Built-in OAuth2, audit trails |
| Data Format Translation | Manual FHIR parsing per model | Declarative schema mapping |
| Multi-EHR Support | Separate integrations per vendor | Single API, multiple sources |

### ROI Metrics

- **Development Time**: 80% reduction in integration effort
- **Time-to-Value**: Deploy trained models in days, not months
- **Maintenance Cost**: Single codebase for all EHR integrations
- **Compliance**: Built-in security patterns reduce audit burden

### Target Users

1. **HealthTech Engineering Teams** - Building clinical AI products
2. **Health System IT** - Deploying internal ML models
3. **Research Institutions** - Productionizing research models
4. **EHR Vendors** - Adding AI capabilities to platforms

---

## Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        EHR Systems                               │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                      │
│  │  Epic   │    │ Cerner  │    │ Medplum │                      │
│  └────┬────┘    └────┬────┘    └────┬────┘                      │
│       │              │              │                            │
│       └──────────────┼──────────────┘                            │
│                      │                                           │
│              ┌───────▼───────┐                                   │
│              │  CDS Hooks /  │  Patient-view, order-select       │
│              │  FHIR API     │  triggers                         │
│              └───────┬───────┘                                   │
└──────────────────────┼──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                 ML Healthcare API                                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  OAuth2 / JWT Layer                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│  ┌────────────┬───────────┼───────────┬────────────────────┐    │
│  │            │           │           │                    │    │
│  │  ┌─────────▼─────────┐ │  ┌────────▼────────┐          │    │
│  │  │   CDS Hooks       │ │  │  FHIR Gateway   │          │    │
│  │  │   Service         │ │  │  (Multi-Source) │          │    │
│  │  └─────────┬─────────┘ │  └────────┬────────┘          │    │
│  │            │           │           │                    │    │
│  │  ┌─────────▼───────────▼───────────▼─────────┐         │    │
│  │  │           ML Pipeline Engine              │         │    │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐  │         │    │
│  │  │  │ Feature  │→│  Impute  │→│ Inference│  │         │    │
│  │  │  │ Extract  │ │  Missing │ │  Engine  │  │         │    │
│  │  │  └──────────┘ └──────────┘ └──────────┘  │         │    │
│  │  └───────────────────────────────────────────┘         │    │
│  │                       │                                │    │
│  │  ┌────────────────────▼────────────────────┐          │    │
│  │  │        Trained ML Model                  │          │    │
│  │  │   (scikit-learn, XGBoost, PyTorch)      │          │    │
│  │  └─────────────────────────────────────────┘          │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. EHR Event (patient chart open)
          ↓
2. CDS Hooks request with prefetched FHIR data
          ↓
3. OAuth2 token validation (if enabled)
          ↓
4. FHIR Bundle → Feature extraction via schema
          ↓
5. ML Pipeline: validate → impute → inference
          ↓
6. Prediction → FHIR RiskAssessment / CDS Card
          ↓
7. Response to EHR → Alert displayed to clinician
```

### Key Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI + HealthChainAPI | High-performance async API |
| **Authentication** | OAuth2 JWT Bearer | Enterprise security |
| **FHIR Processing** | fhir.resources | Type-safe FHIR handling |
| **ML Pipeline** | HealthChain Pipeline | Composable inference |
| **CDS Integration** | CDS Hooks 1.1 | Real-time EHR alerts |
| **Configuration** | Pydantic Settings | Type-safe config |

---

## Deployment Patterns

### Pattern 1: Real-Time CDS Hooks

**Use Case**: Point-of-care clinical decision support

```
Clinician opens chart → EHR triggers patient-view hook →
ML prediction → Alert card displayed in EHR
```

**Characteristics**:
- Sub-second latency requirement
- Event-driven (EHR pushes data)
- Ephemeral alerts (not persisted)
- Prefetch minimizes roundtrips

**Best For**: Sepsis alerts, drug interactions, diagnostic suggestions

### Pattern 2: Batch FHIR Screening

**Use Case**: Population health management

```
Scheduled job → Query FHIR server → Batch predictions →
Create RiskAssessments → Write back to FHIR
```

**Characteristics**:
- Minutes-hours latency acceptable
- Pull-based (API queries data)
- Persisted results (RiskAssessment)
- Pagination for large datasets

**Best For**: Risk stratification, care gap identification

### Pattern 3: Direct API Integration

**Use Case**: Custom applications

```
Application → POST /predict with FHIR Bundle →
Prediction response → Application logic
```

**Characteristics**:
- Application-controlled timing
- Flexible input/output
- OAuth2 protected
- Sync or async

**Best For**: Patient portals, research tools, third-party integrations

---

## Security & Compliance

### Authentication

| Method | Use Case | Configuration |
|--------|----------|---------------|
| OAuth2 JWT | Production APIs | `OAUTH2_ENABLED=true` |
| No Auth | Development/Testing | `OAUTH2_ENABLED=false` |
| mTLS | High-security environments | Via reverse proxy |

### Supported Identity Providers

- Auth0
- Okta
- Azure AD
- Keycloak
- Any OIDC-compliant provider

### Audit Trail

The event system captures:
- All API requests with timestamps
- User identity (from JWT)
- Prediction inputs/outputs
- FHIR queries to external systems

### HIPAA Considerations

| Requirement | Implementation |
|-------------|----------------|
| Access Control | OAuth2 with scope/role enforcement |
| Audit Logging | Event dispatcher with structured logs |
| Encryption | TLS in transit, platform encryption at rest |
| Minimum Necessary | Schema defines exact data extracted |
| BAA | Required with cloud providers |

---

## Integration Guide

### Epic Integration

1. **Register App** in Epic App Orchard
2. **Configure CDS Service** in Epic admin
3. **Set Environment**:
   ```bash
   EPIC_CLIENT_ID=your-app-id
   EPIC_CLIENT_SECRET_PATH=/path/to/private_key.pem
   EPIC_BASE_URL=https://fhir.epic.com/.../api/FHIR/R4
   ```

### Cerner Integration

1. **Register** in Cerner Code Console
2. **Configure** webhook URL
3. **Set Environment**:
   ```bash
   CERNER_CLIENT_ID=your-app-id
   CERNER_CLIENT_SECRET=your-secret
   CERNER_BASE_URL=https://fhir-ehr.cerner.com/r4/tenant
   ```

### Custom FHIR Server

Any FHIR R4 server with OAuth2:
```bash
CUSTOM_CLIENT_ID=...
CUSTOM_BASE_URL=https://your-fhir-server.com/fhir/R4
CUSTOM_TOKEN_URL=https://your-fhir-server.com/oauth2/token
```

---

## Performance Characteristics

### Latency Targets

| Endpoint | Target | Notes |
|----------|--------|-------|
| `/predict` (bundle) | <100ms | Direct inference |
| `/predict/{id}` (query) | <500ms | Includes FHIR fetch |
| CDS Hooks | <200ms | EHR timeout typically 10s |
| Health check | <10ms | No processing |

### Scaling

```yaml
# Kubernetes deployment
replicas: 3-10 (based on load)
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### Throughput

- **Single instance**: ~100 requests/second
- **Horizontal scaling**: Linear with replicas
- **Bottleneck**: Typically FHIR server latency

---

## Cost Considerations

### Infrastructure

| Component | Estimated Cost | Notes |
|-----------|----------------|-------|
| Compute (3 instances) | $150-300/month | Cloud pricing varies |
| Load Balancer | $20-50/month | Managed LB |
| Logging/Monitoring | $50-100/month | Based on volume |
| **Total** | **$220-450/month** | Production deployment |

### Development

| Activity | Effort | With HealthChain |
|----------|--------|------------------|
| FHIR Integration | 2-4 weeks | 1-2 days |
| OAuth2 Setup | 1-2 weeks | Configuration only |
| CDS Hooks | 2-3 weeks | Hours |
| Testing | 2-4 weeks | Built-in sandbox |
| **Total** | **2-3 months** | **1-2 weeks** |

---

## Success Metrics

### Technical KPIs

- API latency P95 < 200ms
- Availability > 99.9%
- Error rate < 0.1%
- Model inference time < 50ms

### Business KPIs

- Time to first deployment
- Number of EHR integrations
- Clinical decision support utilization
- Alert acknowledgment rate

---

## Roadmap Alignment

This implementation supports HealthChain's roadmap:

- Enhanced Docker/Kubernetes support
- Improved multi-source data aggregation
- Extended FHIR resource coverage
- Audit trails and compliance features

---

## Getting Started

```bash
# 1. Clone and install
git clone https://github.com/dotimplement/HealthChain
cd HealthChain
pip install -e ".[ml]"

# 2. Configure
cp ml-app/.env.example ml-app/.env
# Edit .env with your settings

# 3. Train demo model
python ml-app/train_demo_model.py

# 4. Run
python ml-app/app.py

# 5. Test
curl http://localhost:8000/health
curl http://localhost:8000/model/info
```

---

## Support & Resources

- **Documentation**: https://dotimplement.github.io/HealthChain/
- **GitHub**: https://github.com/dotimplement/HealthChain
- **Discord**: https://discord.gg/UQC6uAepUz
- **Issues**: https://github.com/dotimplement/HealthChain/issues
