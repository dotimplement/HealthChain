# FHIR Gateway

The `FHIRGateway` provides a unified **asynchronous** interface for connecting to multiple FHIR servers with automatic authentication, connection pooling, error handling, and simplified CRUD operations. It handles the complexity of managing multiple FHIR clients and provides a consistent API across different healthcare systems.


## Basic Usage

```python
from healthchain.gateway import FHIRGateway
from fhir.resources.patient import Patient

# Create gateway
gateway = FHIRGateway()

# Connect to FHIR server
gateway.add_source(
    "my_fhir_server",
    "fhir://fhir.example.com/api/FHIR/R4/?client_id=your_app&client_secret=secret&token_url=https://fhir.example.com/oauth2/token"
)

async with gateway:
    # FHIR operations
    patient = await gateway.read(Patient, "123", "my_fhir_server")
    print(f"Patient: {patient.name[0].family}")
```


## Adding Sources 🏥

The gateway currently supports adding sources with OAuth2 authentication flow.

```python
# Epic Sandbox (JWT assertion)
gateway.add_source(
    "epic",
    (
        "fhir://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/"
        "?client_id=your_app"
        "&client_secret_path=keys/private.pem"
        "&token_url=https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
        "&use_jwt_assertion=true"
    )
)

# Medplum (Client Credentials)
gateway.add_source(
    "medplum",
    (
        "fhir://api.medplum.com/fhir/R4/"
        "?client_id=your_app"
        "&client_secret=secret"
        "&token_url=https://api.medplum.com/oauth2/token"
        "&scope=openid"
    )
)
```
!!! info "For more information on configuring specific FHIR servers"

    **Epic FHIR API:**

    - [Epic on FHIR Documentation](https://fhir.epic.com/)
    - [Epic OAuth2 Setup](https://fhir.epic.com/Documentation?docId=oauth2)
    - [Test Patients in Epic Sandbox](https://fhir.epic.com/Documentation?docId=testpatients)
    - [Useful Epic Sandbox Setup Guide](https://docs.interfaceware.com/docs/IguanaX_Documentation_Home/Development/iNTERFACEWARE_Collections/HL7_Collection/Epic_FHIR_Adapter/Set_up_your_Epic_FHIR_Sandbox_2783739933/)

    **Medplum FHIR API:**

    - [Medplum app tutorial](https://www.medplum.com/docs/tutorials)
    - [Medplum OAuth2 Client Credentials Setup](https://www.medplum.com/docs/auth/methods/client-credentials)

    **General Resources:**

    - [OAuth2](https://oauth.net/2/)
    - [FHIR RESTful API](https://hl7.org/fhir/http.html)
    - [FHIR Specification](https://hl7.org/fhir/)


### Connection String Format

Connection strings use the `fhir://` scheme with query parameters:

```
fhir://hostname:port/path?param1=value1&param2=value2
```

**Required Parameters:**

- `client_id`: OAuth2 client ID
- `token_url`: OAuth2 token endpoint

**Optional Parameters:**

- `client_secret`: OAuth2 client secret (for client credentials flow)
- `client_secret_path`: Path to private key file (for JWT assertion)
- `scope`: OAuth2 scope (default: "`system/*.read system/*.write`")
- `use_jwt_assertion`: Use JWT assertion flow (default: false)
- `audience`: Token audience (for some servers)


## FHIR Operations 🔥

!!! note Prerequisites
    These examples assume you have already created and configured your gateway as shown in the [Basic Usage](#basic-usage) section above.

### Create Resources

```python
from fhir.resources.patient import Patient
from fhir.resources.humanname import HumanName

# Create a new patient
patient = Patient(
    name=[HumanName(family="Smith", given=["John"])],
    gender="male",
    birthDate="1990-01-01"
)

created_patient = await gateway.create(resource=patient, source="medplum")
print(f"Created patient with ID: {created_patient.id}")
```

### Read Resources

```python
from fhir.resources.patient import Patient

# Read a specific patient (Derrick Lin, Epic Sandbox)
patient = await gateway.read(
    resource_type=Patient,
    fhir_id="eq081-VQEgP8drUUqCWzHfw3",
    source="epic"
    )
```

### Update Resources

```python
from fhir.resources.patient import Patient

# Read, modify, and update
patient = await gateway.read(Patient, "123", "medplum")
patient.name[0].family = "Johnson"
updated_patient = await gateway.update(patient, "medplum")

# Using context manager
async with gateway.modify(Patient, "123", "medplum") as patient:
    patient.active = True
    patient.name[0].given = ["Jane"]
    # Automatic save on exit
```

### Delete Resources

```python
from fhir.resources.patient import Patient

# Delete a patient
success = await gateway.delete(Patient, "123", "medplum")
if success:
    print("Patient deleted successfully")
```

## Search Operations

### Basic Search

```python
from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle

# Search by name
search_params = {"family": "Smith", "given": "John"}
results: Bundle = await gateway.search(Patient, search_params, "epic")

for entry in results.entry:
    patient = entry.resource
    print(f"Found: {patient.name[0].family}, {patient.name[0].given[0]}")
```

### Advanced Search

```python
from fhir.resources.patient import Patient

# Complex search with multiple parameters
search_params = {
    "birthdate": "1990-01-01",
    "gender": "male",
    "address-city": "Boston",
    "_count": 50,
    "_sort": "family"
}

results = await gateway.search(Patient, search_params, "epic")
print(f"Found {len(results.entry)} patients")
```

## Transform Handlers 🤖

Transform handlers allow you to create custom API endpoints that process and enhance FHIR resources with additional logic, AI insights, or data transformations before returning them to clients. These handlers run before the response is sent, enabling real-time data enrichment and processing.

```python
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation

@fhir_gateway.transform(Patient)
async def get_enhanced_patient_summary(id: str, source: str = None) -> Patient:
    """Create enhanced patient summary with AI insights"""

    async with fhir_gateway.modify(Patient, id, source=source) as patient:
        # Get lab results and process with AI
        lab_results = await fhir_gateway.search(
            resource_type=Observation,
            search_params={"patient": id, "category": "laboratory"},
            source=source
        )
        insights = nlp_pipeline.process(patient, lab_results)

        # Add AI summary
        patient.extension = patient.extension or []
        patient.extension.append({
            "url": "http://healthchain.org/fhir/summary",
            "valueString": insights.summary
        })

        return patient

# The handler is automatically called via HTTP endpoint:
# GET /fhir/transform/Patient/123?source=epic
```

## Aggregate Handlers 🔗

Aggregate handlers allow you to combine data from multiple FHIR sources into a single resource. This is useful for creating unified views across different EHR systems or consolidating patient data from various healthcare providers.


```python
from fhir.resources.observation import Observation
from fhir.resources.bundle import Bundle

@gateway.aggregate(Observation)
async def aggregate_vitals(patient_id: str, sources: List[str] = None) -> Bundle:
    """Aggregate vital signs from multiple sources."""
    sources = sources or ["epic", "cerner"]
    all_observations = []

    for source in sources:
        try:
            results = await gateway.search(
                Observation,
                {"patient": patient_id, "category": "vital-signs"},
                source
            )
            processed_observations = process_observations(results)
            all_observations.append(processed_observations)
        except Exception as e:
            print(f"Could not get vitals from {source}: {e}")

    return Bundle(type="searchset", entry=[{"resource": obs} for obs in all_observations])

# The handler is automatically called via HTTP endpoint:
# GET /fhir/aggregate/Observation?patient_id=123&sources=epic&sources=cerner
```

## Server Capabilities

- **GET** `/fhir/metadata` - Returns FHIR-style `CapabilityStatement` of transform and aggregate endpoints
- **GET** `/fhir/status` - Returns Gateway status and connection health


## Connection Pool Management

When you add a connection to a FHIR server, the gateway will automatically add it to a connection pool to manage connections to FHIR servers.


### Pool Configuration

```python
# Create gateway with optimized connection settings
gateway = FHIRGateway(
    max_connections=100,           # Total connections across all sources
    max_keepalive_connections=20,  # Keep-alive connections per source
    keepalive_expiry=30.0,         # Keep connections alive for 30 seconds
)

# Add multiple sources - they share the connection pool
gateway.add_source("epic", "fhir://epic.org/...")
gateway.add_source("cerner", "fhir://cerner.org/...")
gateway.add_source("medplum", "fhir://medplum.com/...")

stats = gateway.get_pool_status()
print(stats)
```
