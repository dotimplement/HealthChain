# Multi-EHR Data Aggregation with HealthChain

Aggregate patient data from multiple Electronic Health Record (EHR) systems into unified, actionable records for comprehensive patient care and analytics.

## What It Does

```python
# Connect to multiple EHR systems
aggregator = MultiEHRAggregator(config)
await aggregator.initialize_gateways()

# Aggregate patient data across all systems
patient_record = await aggregator.aggregate_patient_data("patient-123")

# Get unified analytics
analytics = aggregator.get_patient_analytics("patient-123")
print(analytics.generate_summary())
```

This application solves **care fragmentation** by:
- Connecting to Epic, Cerner, athenahealth, and other FHIR-enabled EHR systems
- Aggregating patient data (observations, conditions, medications, procedures)
- Deduplicating resources across systems
- Generating comprehensive patient analytics
- Identifying care gaps and quality measures

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd multi_ehr_aggregation

# Install dependencies
pip install healthchain fhir.resources pydantic pandas

# Configure EHR sources
cp config/.env.example config/.env
# Edit config/ehr_sources.yaml with your EHR endpoints

# Run basic example
python examples/basic_aggregation.py
```

## Use Cases

| Use Case | Description | Key Features |
|----------|-------------|--------------|
| **Patient 360° View** | Complete patient history across providers | Multi-source aggregation, deduplication |
| **Population Health** | Analyze cohorts across health systems | Batch processing, analytics export |
| **Care Coordination** | Share complete records between providers | Data quality metrics, timeline views |
| **Clinical Research** | Aggregate multi-site patient data | Normalized codes, FHIR-compliant export |
| **Quality Reporting** | Identify care gaps and quality measures | Gap analysis, risk stratification |

## Features

### Multi-Source Connectivity
- **Supported EHR Systems**: Epic, Cerner, athenahealth, Allscripts, Meditech, eClinicalWorks
- **Authentication**: OAuth2, Basic Auth, API Key
- **Standards**: HL7 FHIR R4 compliant
- **Resilient**: Retry logic, error handling per source

### Data Aggregation
- **Resources**: Patient demographics, Observations, Conditions, Medications, Procedures
- **Deduplication**: Intelligent matching across sources
- **Normalization**: Code mapping (ICD-9/10, SNOMED, LOINC)
- **Timeline**: Chronological view of all clinical events

### Analytics & Insights
- **Data Quality Metrics**: Completeness, consistency, freshness scores
- **Clinical Insights**: Active conditions, medication lists, procedure history
- **Care Gap Identification**: Missing screenings, overdue labs, preventive care
- **Risk Flags**: Polypharmacy, multiple chronic conditions, care fragmentation

### Export & Integration
- **Formats**: JSON, CSV, Parquet
- **Use Cases**: Analytics pipelines, BI tools, data lakes
- **Compliance**: Source attribution, audit trails

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Multi-EHR Aggregator                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Epic Gateway │  │Cerner Gateway│  │Athena Gateway│ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                 │          │
│         └─────────────────┴─────────────────┘          │
│                           │                            │
│                  ┌────────▼────────┐                   │
│                  │  FHIRGateway    │                   │
│                  │  (HealthChain)  │                   │
│                  └────────┬────────┘                   │
│                           │                            │
│         ┌─────────────────┴─────────────────┐          │
│         │                                   │          │
│  ┌──────▼────────┐              ┌──────────▼──────┐   │
│  │ Deduplication │              │  Normalization  │   │
│  │ & Merging     │              │  & Validation   │   │
│  └──────┬────────┘              └──────────┬──────┘   │
│         │                                   │          │
│         └─────────────────┬─────────────────┘          │
│                           │                            │
│                  ┌────────▼────────┐                   │
│                  │  Aggregated     │                   │
│                  │  Patient Record │                   │
│                  └────────┬────────┘                   │
│                           │                            │
│         ┌─────────────────┴─────────────────┐          │
│         │                                   │          │
│  ┌──────▼────────┐              ┌──────────▼──────┐   │
│  │  Analytics    │              │     Export      │   │
│  │  Generation   │              │  JSON/CSV/PKT   │   │
│  └───────────────┘              └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### EHR Sources (`config/ehr_sources.yaml`)

```yaml
ehr_sources:
  - name: "Epic_MainHospital"
    base_url: "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
    system_type: "Epic"
    auth_type: "oauth2"
    priority: 1
    credentials:
      client_id: "${EPIC_CLIENT_ID}"
      client_secret: "${EPIC_CLIENT_SECRET}"
```

### Aggregation Settings

```yaml
aggregation:
  deduplication_enabled: true
  normalize_codes: true
  merge_strategy: "priority"  # Use highest priority source
```

### Data Quality

```yaml
data_quality:
  min_completeness_score: 0.5
  max_data_age_days: 90
  validate_fhir_resources: true
```

## Examples

### Basic Aggregation

```python
from app import MultiEHRAggregator, MultiEHRConfig
from models.patient_record import EHRSource

config = MultiEHRConfig(
    ehr_sources=[
        EHRSource(name="Epic", base_url="https://..."),
        EHRSource(name="Cerner", base_url="https://..."),
    ]
)

aggregator = MultiEHRAggregator(config)
await aggregator.initialize_gateways()

# Aggregate data
record = await aggregator.aggregate_patient_data("patient-123")
print(f"Found {len(record.observations)} observations")
```

### Batch Processing

```python
patient_ids = ["pt-001", "pt-002", "pt-003"]

for patient_id in patient_ids:
    record = await aggregator.aggregate_patient_data(patient_id)
    # Process record...

# Export all data
aggregator.export_data(Path("data/batch_output.json"))
```

### Analytics Generation

```python
# Generate analytics
analytics = aggregator.get_patient_analytics("patient-123")

print(f"Data Sources: {analytics.data_sources}")
print(f"Active Conditions: {analytics.condition_stats.active_count}")
print(f"Data Completeness: {analytics.completeness_score:.1%}")

# Check for care gaps
if analytics.care_gaps.missing_screenings:
    print("Missing screenings:", analytics.care_gaps.missing_screenings)
```

## Data Models

### AggregatedPatientRecord

Main data structure for aggregated patient data:

```python
class AggregatedPatientRecord:
    patient_identifier: str
    patient: Optional[Patient]  # Demographics
    observations: List[Observation]
    conditions: List[Condition]
    medications: List[MedicationRequest]
    procedures: List[Procedure]
    sources: Dict[str, Dict]  # Data by source
    quality_metrics: DataQualityMetrics
```

### PatientAnalytics

Analytics and insights:

```python
class PatientAnalytics:
    data_sources: int
    total_observations: int
    total_conditions: int
    completeness_score: float
    care_gaps: CareGaps
    risk_flags: List[str]
```

## API Reference

### MultiEHRAggregator

#### `initialize_gateways()`
Connect to all configured EHR sources.

#### `aggregate_patient_data(patient_identifier, identifier_system)`
Aggregate data for a specific patient across all sources.

**Returns**: `AggregatedPatientRecord`

#### `get_patient_analytics(patient_identifier)`
Generate analytics for an aggregated patient.

**Returns**: `PatientAnalytics`

#### `export_data(output_path, format)`
Export aggregated data to file.

**Formats**: `json`, `csv`, `parquet`

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_aggregation.py -v

# With coverage
pytest --cov=. tests/
```

## Production Deployment

### Security Considerations

- **Credentials**: Use environment variables, never commit secrets
- **OAuth2**: Implement proper token refresh and management
- **HIPAA Compliance**: Ensure BAA with EHR vendors
- **Audit Logging**: Enable comprehensive audit trails
- **Data Encryption**: Encrypt data at rest and in transit

### Performance Optimization

```python
config = MultiEHRConfig(
    # Process sources concurrently
    performance={
        "max_concurrent_sources": 5,
        "request_timeout_seconds": 30,
        "cache_ttl_minutes": 15
    }
)
```

### Monitoring

- Track aggregation success rates per source
- Monitor data quality metrics over time
- Alert on failed EHR connections
- Log processing times and bottlenecks

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Connection timeout** | Check EHR endpoint availability, increase timeout |
| **Auth failures** | Verify credentials, check token expiration |
| **No data returned** | Confirm patient ID format, check patient exists in system |
| **Duplicate data** | Enable deduplication, verify dedup rules |
| **Code mismatches** | Enable code normalization, check terminology mappings |

## Support

- **Documentation**: See `IMPLEMENTATION_GUIDELINES.md` for detailed setup
- **Technical Details**: See `TECHNICAL_SUMMARY.md` for architecture
- **Business Context**: See `BUSINESS_SUMMARY.md` for ROI and use cases
- **Issues**: Open GitHub issue for bugs or feature requests

## License

See main HealthChain repository for license information.

## Contributing

Contributions welcome! See main HealthChain `CONTRIBUTING.md` for guidelines.
