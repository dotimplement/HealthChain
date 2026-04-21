# Cookbook

Hands-on, production-ready examples for building healthcare AI applications with HealthChain.

<div class="tag-legend">
  <span class="tag-legend-title">Filter:</span>
  <span class="tag tag-filter tag-beginner" data-tag="beginner">Beginner</span>
  <span class="tag tag-filter tag-intermediate" data-tag="intermediate">Intermediate</span>
  <span class="tag tag-filter tag-advanced" data-tag="advanced">Advanced</span>
  <span class="tag tag-filter tag-healthtech" data-tag="healthtech">HealthTech</span>
  <span class="tag tag-filter tag-genai" data-tag="genai">GenAI</span>
  <span class="tag tag-filter tag-ml" data-tag="ml">ML Research</span>
  <span class="tag tag-filter tag-gateway" data-tag="gateway">Gateway</span>
  <span class="tag tag-filter tag-pipeline" data-tag="pipeline">Pipeline</span>
  <span class="tag tag-filter tag-interop" data-tag="interop">Interop</span>
  <span class="tag tag-filter tag-fhir" data-tag="fhir">FHIR</span>
  <span class="tag tag-filter tag-cdshooks" data-tag="cdshooks">CDS Hooks</span>
  <span class="tag tag-filter tag-sandbox" data-tag="sandbox">Sandbox</span>
  <span class="tag-clear hidden" id="clearFilters">Clear</span>
</div>

<div class="cookbook-wrapper">
<div class="cookbook-grid" id="cookbookGrid">

<a href="setup_fhir_sandboxes/" class="cookbook-card" data-tags="fhir sandbox beginner">
  <div class="cookbook-card-icon">🚦</div>
  <div class="cookbook-card-title">Working with FHIR Sandboxes</div>
  <div class="cookbook-card-description">
    Spin up and access free Epic, Medplum, and other FHIR sandboxes for safe experimentation. Recommended first step before the other tutorials.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-beginner">Beginner</span>
    <span class="tag tag-fhir">FHIR</span>
    <span class="tag tag-sandbox">Sandbox</span>
  </div>
</a>

<a href="ml_model_deployment/" class="cookbook-card" data-tags="ml gateway cdshooks intermediate">
  <div class="cookbook-card-icon">🔬</div>
  <div class="cookbook-card-title">Deploy ML Models: Real-Time Alerts & Batch Screening</div>
  <div class="cookbook-card-description">
    Deploy the same ML model two ways: CDS Hooks for point-of-care sepsis alerts, and FHIR Gateway for population-level batch screening with RiskAssessment resources.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-intermediate">Intermediate</span>
    <span class="tag tag-ml">ML Research</span>
    <span class="tag tag-gateway">Gateway</span>
    <span class="tag tag-cdshooks">CDS Hooks</span>
  </div>
</a>

<a href="fhir_qa/" class="cookbook-card" data-tags="genai fhir pipeline gateway beginner">
  <div class="cookbook-card-icon">💬</div>
  <div class="cookbook-card-title">FHIR-Grounded Patient Q&A</div>
  <div class="cookbook-card-description">
    Build a patient Q&A service that fetches live FHIR data, formats it as LLM context via a pipeline, and returns grounded answers. Foundation pattern for patient portal chatbots and care navigation assistants.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-beginner">Beginner</span>
    <span class="tag tag-genai">GenAI</span>
    <span class="tag tag-fhir">FHIR</span>
    <span class="tag tag-pipeline">Pipeline</span>
    <span class="tag tag-gateway">Gateway</span>
  </div>
</a>

<a href="multi_ehr_aggregation/" class="cookbook-card" data-tags="genai gateway fhir intermediate">
  <div class="cookbook-card-icon">🔗</div>
  <div class="cookbook-card-title">Multi-Source Patient Data Aggregation</div>
  <div class="cookbook-card-description">
    Merge patient data from multiple FHIR sources (Epic, Cerner, etc.), deduplicate conditions, prove provenance, and handle cross-vendor errors. Foundation for RAG and analytics workflows.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-intermediate">Intermediate</span>
    <span class="tag tag-genai">GenAI</span>
    <span class="tag tag-gateway">Gateway</span>
    <span class="tag tag-fhir">FHIR</span>
  </div>
</a>

<a href="clinical_coding/" class="cookbook-card" data-tags="healthtech pipeline interop advanced">
  <div class="cookbook-card-icon">🧾</div>
  <div class="cookbook-card-title">Automate Clinical Coding & FHIR Integration</div>
  <div class="cookbook-card-description">
    Extract medical conditions from clinical documentation using AI, map to SNOMED CT codes, and sync as FHIR Condition resources for billing, analytics, and interoperability.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-advanced">Advanced</span>
    <span class="tag tag-healthtech">HealthTech</span>
    <span class="tag tag-pipeline">Pipeline</span>
    <span class="tag tag-interop">Interop</span>
  </div>
</a>

<a href="discharge_summarizer/" class="cookbook-card" data-tags="healthtech gateway cdshooks beginner">
  <div class="cookbook-card-icon">📝</div>
  <div class="cookbook-card-title">Summarize Discharge Notes with CDS Hooks</div>
  <div class="cookbook-card-description">
    Deploy a CDS Hooks-compliant service that listens for discharge events, auto-generates concise plain-language summaries, and delivers actionable clinical cards directly into the EHR workflow.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-beginner">Beginner</span>
    <span class="tag tag-healthtech">HealthTech</span>
    <span class="tag tag-gateway">Gateway</span>
    <span class="tag tag-cdshooks">CDS Hooks</span>
  </div>
</a>

<a href="format_conversion/" class="cookbook-card" data-tags="healthtech interop fhir intermediate">
  <div class="cookbook-card-icon">🔄</div>
  <div class="cookbook-card-title">Convert Between Healthcare Data Formats</div>
  <div class="cookbook-card-description">
    Convert between CDA, HL7v2, and FHIR formats using the interoperability engine. Handle bidirectional conversion for integrating legacy systems with modern FHIR applications.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-intermediate">Intermediate</span>
    <span class="tag tag-healthtech">HealthTech</span>
    <span class="tag tag-interop">Interop</span>
    <span class="tag tag-fhir">FHIR</span>
  </div>
</a>

<div class="no-results hidden" id="noResults">
  No cookbooks match the selected filters. <a href="#" onclick="clearAllFilters(); return false;">Clear filters</a>
</div>

</div>
</div>

---

## From cookbook to service

Cookbooks are standalone scripts — run them directly to explore and experiment. When you're ready to build a proper service, scaffold a project and move your logic in:

```bash
# 1. Run a cookbook locally
python cookbook/sepsis_cds_hooks.py

# 2. Scaffold a project
healthchain new my-sepsis-service -t cds-hooks
cd my-sepsis-service

# 3. Move your hook logic into app.py, then run with config
healthchain serve
```

`app.run()` (used in cookbooks) is a convenience wrapper — equivalent to running uvicorn directly. `healthchain serve` reads `healthchain.yaml` for port, TLS, and deployment settings, and prints a startup banner so you can see what's active at a glance.

**What moves from your script into `healthchain.yaml`:**

```python
# cookbook — everything hardcoded in Python
gateway = FHIRGateway()
gateway.add_source("medplum", FHIRAuthConfig.from_env("MEDPLUM").to_connection_string())

llm = ChatAnthropic(model="claude-opus-4-6", max_tokens=512)

app = HealthChainAPI(title="My App", service_type="fhir-gateway")
app.run(port=8000)
```

```yaml
# healthchain.yaml — port, sources, and LLM provider declared here
service:
  type: fhir-gateway
  port: 8000

sources:
  medplum:
    env_prefix: MEDPLUM   # credentials stay in .env

llm:
  provider: anthropic
  model: claude-opus-4-6
  max_tokens: 512
```

```python
# app.py — load from config instead
from healthchain.config.appconfig import AppConfig
from healthchain.gateway import FHIRGateway, HealthChainAPI

config = AppConfig.load()
gateway = FHIRGateway.from_config(config)
llm = config.llm.to_langchain()

app = HealthChainAPI(title="My App")
```

Credentials (API keys, client secrets) always stay in `.env` — never in `healthchain.yaml`.

!!! tip "Configuration reference"
    See the [configuration reference](../reference/config.md) for all available settings — security, compliance, eval, and more.
