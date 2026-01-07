<div align="center" style="margin-bottom: 1em;">

# HealthChain 💫 🏥

<img src="https://raw.githubusercontent.com/dotimplement/HealthChain/main/docs/assets/images/healthchain_logo.png" alt="HealthChain Logo" width=300></img>

<!-- Project Badges -->
[![PyPI Version][pypi-version-badge]][pypi]
[![Stars][stars-badge]][stars]
[![Downloads][downloads-badge]][pypistats]

[![License][license-badge]][license]
[![Python Versions][python-versions-badge]][pypi]
[![Build Status][build-badge]][build]
[![AI-Assisted Development][ai-badge]][claude-md]

[![Substack][substack-badge]][substack]
[![Discord][discord-badge]][discord]



</div>

<h2 align="center" style="border-bottom: none">Open-Source Framework for Productionizing Healthcare AI</h2>


<div align="center">

HealthChain is an open-source developer framework to build healthcare AI applications with native protocol understanding. Skip months of custom integration with **built-in FHIR support**, **real-time EHR connectivity**, and **production-ready deployment** - all in Python.

</div>

## Installation

```bash
pip install healthchain
```

## Core Features

HealthChain is the **quickest way for AI/ML engineers to integrate their models with real healthcare systems**.


### 💡 For HealthTech Engineers

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/dotimplement/HealthChain/main/docs/assets/images/hc-use-cases-clinical-integration.png" alt="Clinical Integration" width=100%>
      <div align="center">
        <br>
        <a href="https://dotimplement.github.io/HealthChain/reference/gateway/cdshooks/"><strong>⚡️ Real-Time Clinical Workflow Integration</strong></a>
        <br><br>
        <div>Build CDS alerts and automated coding tools that integrate directly into Epic workflows</div><br>
        <a href="https://dotimplement.github.io/HealthChain/cookbook/discharge_summarizer/">Getting Started →</a>
        <br><br>
      </div>
    </td>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/dotimplement/HealthChain/main/docs/assets/images/openapi_docs.png" alt="FHIR Utilities" width=100%>
      <div align="center">
        <br>
        <a href="https://dotimplement.github.io/HealthChain/reference/utilities/fhir_helpers/"><strong>🔥 FHIR Development Utilities</strong></a>
        <br><br>
        <div>Accelerate development with type-safe FHIR resource creation, validation helpers, and sandbox environments for testing clinical workflows</div><br>
        <a href="https://dotimplement.github.io/HealthChain/reference/utilities/sandbox/">Getting Started →</a>
        <br><br>
      </div>
    </td>
  </tr>
</table>



### 🤖 For LLM / GenAI Developers

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/dotimplement/HealthChain/main/docs/assets/images/hc-use-cases-genai-aggregate.png" alt="Multi-Source Integration" width=100%>
      <div align="center">
        <br>
        <a href="https://dotimplement.github.io/HealthChain/reference/gateway/gateway/"><strong>🔌 Multi-EHR Data Aggregation</strong></a>
        <br><br>
        <div>Aggregate patient data from multiple FHIR sources into unified records with built-in NLP processing and automatic deduplication</div><br>
        <a href="https://dotimplement.github.io/HealthChain/cookbook/multi_ehr_aggregation/">Getting Started →</a>
        <br><br>
      </div>
    </td>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/dotimplement/HealthChain/main/docs/assets/images/interopengine.png" alt="Format Conversion" width=100%>
      <div align="center">
        <br>
        <a href="https://dotimplement.github.io/HealthChain/reference/interop/interop/"><strong>🔄 Healthcare Data Format Conversion</strong></a>
        <br><br>
        <div>Convert between FHIR and CDA formats with configuration-driven templates for unified data processing workflows</div><br>
        <a href="https://dotimplement.github.io/HealthChain/cookbook/clinical_coding/">Getting Started →</a>
        <br><br>
      </div>
    </td>
  </tr>
</table>

### 🎓 For ML Researchers


<table>
  <tr>
    <td width="50%" valign="top">
    <div align="center">
      <img src="https://raw.githubusercontent.com/dotimplement/HealthChain/main/docs/assets/images/hc-use-cases-ml-deployment.png" alt="Deploy" width=60%>
    </div>
      <div align="center">
        <br>
        <a href="https://dotimplement.github.io/HealthChain/reference/gateway/fhir_gateway/"><strong>🚀 Deploy ML Models as Healthcare APIs</strong></a>
        <br><br>
        <div>Turn any trained model into a production-ready FHIR endpoint with OAuth2 authentication and type-safe healthcare data handling</div><br>
        <a href="https://dotimplement.github.io/HealthChain/cookbook/ml_model_deployment/">Getting Started →</a>
        <br><br>
      </div>
    </td>
</table>


## Why HealthChain?

**Electronic health record (EHR) data is specific, complex, and fragmented.** Most healthcare AI projects require months of manual integration and custom validation on top of model development. This leads to fragile pipelines that break easily and consume valuable developer time.

HealthChain understands healthcare protocols and data formats natively, so you don't have to build that knowledge from scratch. Skip months of custom integration work and productionize your healthcare AI faster.

- **Optimized for real-time** - Connect to live FHIR APIs and integration points instead of stale data exports
- **Automatic validation** - Type-safe FHIR models prevent broken healthcare data
- **Built-in NLP support** - Extract structured data from clinical notes, output as FHIR
- **Developer experience** - Modular and extensible architecture works across any EHR system

## 🏆 Recognition & Community

**Featured & Presented:**
- [Featured by Medplum](https://www.medplum.com/blog/healthchain) for open source integration with Epic
- Featured in [TLDR AI Newsletter](https://tldr.tech/ai/2025-08-21) (900K+ developers)
- Presented at [NHS Python Open Source Conference](https://github.com/nhs-r-community/conference-2024/blob/main/Talks/2024-11-21_jiang-kells_building-healthchain.md) ([watch talk](https://www.youtube.com/watch?v=_ZqlPsDUdSY&t=1967s))
- [Built from NHS AI deployment experience](https://open.substack.com/pub/jenniferjiangkells/p/healthchain-building-the-tool-i-wish) – read the origin story

## 🤝 Partnerships & Production Use

Exploring HealthChain for your product or organization? Drop in our [weekly office hours](https://meet.google.com/zwh-douu-pky) (Thursdays 4.30pm - 5.30pm GMT) or [get in touch](mailto:jenniferjiangkells@gmail.com) to discuss integrations, pilots, or collaborations.

## Usage Examples

### Building a Pipeline [[Docs](https://dotimplement.github.io/HealthChain/reference/pipeline/pipeline)]

```python
from healthchain.pipeline import Pipeline
from healthchain.pipeline.components.integrations import SpacyNLP
from healthchain.io import Document

# Create medical NLP pipeline
nlp_pipeline = Pipeline[Document]()
nlp_pipeline.add_node(SpacyNLP.from_model_id("en_core_web_sm"))

nlp = nlp_pipeline.build()
doc = Document("Patient presents with hypertension and diabetes.")
result = nlp(doc)

spacy_doc = result.nlp.get_spacy_doc()
print(f"Entities: {[(ent.text, ent.label_) for ent in spacy_doc.ents]}")
print(f"FHIR conditions: {result.fhir.problem_list}")  # Auto-converted to FHIR Bundle
```

### Creating a Gateway [[Docs](https://dotimplement.github.io/HealthChain/reference/gateway/gateway)]

```python
from healthchain.gateway import HealthChainAPI, FHIRGateway
from fhir.resources.patient import Patient

# Create healthcare application
app = HealthChainAPI(title="Multi-EHR Patient Data")

# Connect to multiple FHIR sources
fhir = FHIRGateway()
fhir.add_source("epic", "fhir://fhir.epic.com/r4?client_id=epic_client_id")
fhir.add_source("cerner", "fhir://fhir.cerner.com/r4?client_id=cerner_client_id")

@fhir.aggregate(Patient)
def enrich_patient_data(id: str, source: str) -> Patient:
    """Get patient data from any connected EHR and add AI enhancements"""
    bundle = fhir.search(
        Patient,
        {"_id": id},
        source,
        add_provenance=True,
        provenance_tag="ai-enhanced",
    )
    return bundle

app.register_gateway(fhir)

# Available at: GET /fhir/transform/Patient/123?source=epic
# Available at: GET /fhir/transform/Patient/123?source=cerner

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)
```

### Testing with Sandbox [[Docs](https://dotimplement.github.io/HealthChain/reference/utilities/sandbox)]

```python
from healthchain.sandbox import SandboxClient

# Test CDS Hooks service with synthetic data
client = SandboxClient(
    url="http://localhost:8000/cds/cds-services/discharge-summary",
    workflow="encounter-discharge"
)

# Load from test datasets
client.load_from_registry(
    "synthea-patient",
    data_dir="./data/synthea",
    resource_types=["Condition", "DocumentReference"],
    sample_size=5
)

# Send requests and save results
responses = client.send_requests()
client.save_results("./output/")
```

## 🛣️ Road Map

- [ ] 🔍 Data provenance and observability
- [ ] 🔒 Production security and compliance (Authentication, audit logging, HIPAA)
- [ ] 🔄 HL7v2 parsing, FHIR profile conversion and OMOP mapping support
- [ ] 🚀 Enhanced deployment support (Docker, Kubernetes, telemetry)
- [ ] 📊 Model performance monitoring with MLFlow integration
- [ ] 🤖 MCP server integration


## 🤝 Contributing

HealthChain is built for production healthcare systems. We prioritize contributors with:

- **Healthcare product experience** – shipped clinical systems, EHR integrations, or health data products
- **FHIR expertise** – designed or implemented FHIR APIs and interoperability solutions
- **Healthcare security background** – auth, privacy, compliance in regulated environments

If that's you, we'd love your input!

**Get started:**
- See the [project board](https://github.com/orgs/dotimplement/projects/1/views/1) for current roadmap and active work
- Read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines and RFC process
- Discuss ideas in [GitHub Discussions](https://github.com/dotimplement/HealthChain/discussions)
- Join our [Discord](https://discord.gg/UQC6uAepUz) community


## 🤗 Acknowledgements
This project builds on [fhir.resources](https://github.com/nazrulworld/fhir.resources) and [CDS Hooks](https://cds-hooks.org/) standards developed by [HL7](https://www.hl7.org/) and [Boston Children's Hospital](https://www.childrenshospital.org/).


<!-- Badge Links -->
[pypi-version-badge]: https://img.shields.io/pypi/v/healthchain?logo=python&logoColor=white&style=flat-square&color=%23e59875
[downloads-badge]: https://img.shields.io/pepy/dt/healthchain?style=flat-square&color=%2379a8a9
[stars-badge]: https://img.shields.io/github/stars/dotimplement/HealthChain?style=flat-square&logo=github&color=BD932F&logoColor=white
[license-badge]: https://img.shields.io/github/license/dotimplement/HealthChain?style=flat-square&color=%23e59875
[python-versions-badge]: https://img.shields.io/pypi/pyversions/healthchain?style=flat-square&color=%23eeeeee
[build-badge]: https://img.shields.io/github/actions/workflow/status/dotimplement/healthchain/ci.yml?branch=main&style=flat-square&color=%2379a8a9
[discord-badge]: https://img.shields.io/badge/chat-%235965f2?style=flat-square&logo=discord&logoColor=white
[substack-badge]: https://img.shields.io/badge/Cool_Things_In_HealthTech-%23c094ff?style=flat-square&logo=substack&logoColor=white
[ai-badge]: https://img.shields.io/badge/AI--dev_friendly-CLAUDE.MD-%23e59875?style=flat-square&logo=anthropic&logoColor=white

[pypi]: https://pypi.org/project/healthchain/
[pypistats]: https://pepy.tech/project/healthchain
[stars]: https://github.com/dotimplement/HealthChain/stargazers
[license]: https://github.com/dotimplement/HealthChain/blob/main/LICENSE
[build]: https://github.com/dotimplement/HealthChain/actions?query=branch%3Amain
[discord]: https://discord.gg/UQC6uAepUz
[substack]: https://jenniferjiangkells.substack.com/
[claude-md]: CLAUDE.MD
