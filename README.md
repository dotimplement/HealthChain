<div align="center" style="margin-bottom: 1em;">

# HealthChain 💫 🏥

<img src="https://raw.githubusercontent.com/healthchainai/HealthChain/main/docs/assets/images/healthchain_logo.png" alt="HealthChain Logo" width=300></img>

<!-- Project Badges -->

[![PyPI Version][pypi-version-badge]][pypi]
[![Stars][stars-badge]][stars]
[![Downloads][downloads-badge]][pypistats]

[![License][license-badge]][license]
[![Python Versions][python-versions-badge]][pypi]
[![Build Status][build-badge]][build]
[![AI-Assisted Development][ai-badge]][claude-md]
[![DOI](https://zenodo.org/badge/785158333.svg)](https://doi.org/10.5281/zenodo.20056729)

[![Substack][substack-badge]][substack]
[![Discord][discord-badge]][discord]

</div>

<h2 align="center" style="border-bottom: none">Open-Source SDK for Healthcare AI Integration</h2>

<div align="center">

HealthChain is an open-source Python SDK for connecting AI models to live clinical systems. The models aren't the bottleneck — the integration is. Get **built-in FHIR support**, **real-time EHR connectivity**, and **production-ready deployment tooling** without building it from scratch.

</div>

## Installation

```bash
pip install healthchain
```

## Quick Start

```bash
# Scaffold a FHIR Gateway project
healthchain new my-app -t fhir-gateway
cd my-app

# Run locally
healthchain serve
```

<div align="center">
  <img src="https://raw.githubusercontent.com/healthchainai/HealthChain/main/docs/assets/images/demo.gif" alt="HealthChain CLI demo" width="700">
</div>

Edit `app.py` to add your model, and `healthchain.yaml` to configure compliance, security, and deployment settings.

See the [CLI reference](https://healthchainai.github.io/HealthChain/cli/) for all commands.

## Core Features

The quickest way for AI developers and researchers to ship healthcare AI — everything you need out of the box, built to scale with you.

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/healthchainai/HealthChain/main/docs/assets/images/hc-use-cases-genai-aggregate.png" alt="Multi-Source Integration" width=100%>
      <div align="center">
        <br>
        <a href="https://healthchainai.github.io/HealthChain/reference/gateway/gateway/"><strong>🔌 Multi-EHR Data Aggregation</strong></a>
        <br><br>
        <div>Aggregate patient data from multiple FHIR sources into unified records with built-in NLP processing and automatic deduplication</div><br>
        <a href="https://healthchainai.github.io/HealthChain/cookbook/multi_ehr_aggregation/">Getting Started →</a>
        <br><br>
      </div>
    </td>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/healthchainai/HealthChain/main/docs/assets/images/hc-use-cases-ml-deployment.png" alt="Deploy" width=100%>
      <div align="center">
        <br>
        <a href="https://healthchainai.github.io/HealthChain/reference/gateway/fhir_gateway/"><strong>🚀 Deploy ML Models as Healthcare APIs</strong></a>
        <br><br>
        <div>Turn any trained model into a production-ready FHIR endpoint with OAuth2 authentication and type-safe healthcare data handling</div><br>
        <a href="https://healthchainai.github.io/HealthChain/cookbook/ml_model_deployment/">Getting Started →</a>
        <br><br>
      </div>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/healthchainai/HealthChain/main/docs/assets/images/openapi_docs.png" alt="FHIR Utilities" width=100%>
      <div align="center">
        <br>
        <a href="https://healthchainai.github.io/HealthChain/reference/utilities/fhir_helpers/"><strong>🔥 FHIR Development Utilities</strong></a>
        <br><br>
        <div>Type-safe FHIR resource creation, validation helpers, and sandbox environments — skip the boilerplate and work with healthcare data natively</div><br>
        <a href="https://healthchainai.github.io/HealthChain/reference/utilities/sandbox/">Getting Started →</a>
        <br><br>
      </div>
    </td>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/healthchainai/HealthChain/main/docs/assets/images/hc-use-cases-clinical-integration.png" alt="Clinical Integration" width=100%>
      <div align="center">
        <br>
        <a href="https://healthchainai.github.io/HealthChain/reference/gateway/cdshooks/"><strong>⚡️ Real-Time Clinical Workflow Integration</strong></a>
        <br><br>
        <div>Deploy AI models as CDS services that integrate directly into EHR workflows — alerts, recommendations, and automated coding at the point of care</div><br>
        <a href="https://healthchainai.github.io/HealthChain/cookbook/discharge_summarizer/">Getting Started →</a>
        <br><br>
      </div>
    </td>
  </tr>
</table>

## Why HealthChain?

Every serious healthcare AI project builds the same integration infrastructure from scratch. Whether you're deploying a logistic regression or a 70B parameter model, the wall between a trained model and a live clinical system is the same: real FHIR APIs, multi-site deployments, auditable governance. No off-the-shelf solution exists, and engineers who understand both AI and healthcare protocols are scarce and hard to retain.

HealthChain handles that complexity so you can focus on what actually matters: the model and the patient.

- **Optimized for real-time** - Connect to live FHIR APIs and integration points instead of stale data exports
- **Automatic validation** - Type-safe FHIR models prevent broken healthcare data
- **Native LLM + ML support** - Wire up any model, from LLMs to scikit-learn, and output results as FHIR
- **Works with your existing stack** - Integrates with FastAPI, LangChain, HuggingFace, and spaCy
- **Production-ready foundations** - Dockerized deployment, configurable security, and an architecture built for NHS and HIPAA environments

## 🏆 Recognition & Community

**Featured & Presented:**

- Featured in [TLDR AI Newsletter](https://tldr.tech/ai/2025-08-21) (900K+ developers)
- [Featured by Medplum](https://www.medplum.com/blog/healthchain) for open source integration with Epic
- Presented at [NHS Python Open Source Conference](https://github.com/nhs-r-community/conference-2024/blob/main/Talks/2024-11-21_jiang-kells_building-healthchain.md) ([watch talk](https://www.youtube.com/watch?v=_ZqlPsDUdSY&t=1967s))
- [Built from NHS AI deployment experience](https://open.substack.com/pub/jenniferjiangkells/p/healthchain-building-the-tool-i-wish) – read the origin story

## 🤝 Partnerships & Production Use

Exploring HealthChain for your product or organization? [Get in touch](mailto:jenniferjiangkells@gmail.com) to discuss integrations, pilots, or collaborations, or join our [Discord](https://discord.gg/UQC6uAepUz) to connect with the community.

## Usage Examples

### Creating a Gateway [[Docs](https://healthchainai.github.io/HealthChain/reference/gateway/gateway)]

```python
from healthchain.gateway import HealthChainAPI, FHIRGateway
from healthchain.fhir.r4b import Patient

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
    app.run(port=8888)
```

### Building a Pipeline [[Docs](https://healthchainai.github.io/HealthChain/reference/pipeline/pipeline)]

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

## 🛣️ What we're building towards

- [ ] 🔒 **Production security and compliance** — API authentication, audit logging, and configurable security for NHS/HIPAA deployments
- [ ] 📋 **Governance as config** — clinical safety, data access agreements, and compliance standards as a first-class deployment artifact in `healthchain.yaml`
- [ ] 🔌 **Deeper EHR connectivity** — more FHIR sources, live data patterns, and real-world integration examples from pilot deployments
- [ ] 📊 **Observability** — deployment telemetry and audit trails for healthcare systems
- [ ] 🤖 **Agentic integrations** — support for AI agent frameworks and agentic healthcare workflows

## 🤝 Contributing

HealthChain is built by and for the next generation of healthcare developers — researchers moving models from retrospective data into live systems, AI developers who don't want to spend months learning FHIR before they can ship anything. The best contributions come from people who have hit a real problem and have something specific to say about it.

**Get started:**

- **Working with healthcare or research data?** [Contribute a cookbook](https://github.com/healthchainai/HealthChain/issues/208) — bring your use case, I'll personally support you through it
- Read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- Technical questions and ideas → [GitHub Discussions](https://github.com/healthchainai/HealthChain/discussions)
- Pilots and partnerships → [email](mailto:jenniferjiangkells@gmail.com?subject=HealthChain)

## 🤗 Acknowledgements

This project builds on [fhir.resources](https://github.com/nazrulworld/fhir.resources) and [CDS Hooks](https://cds-hooks.org/) standards developed by [HL7](https://www.hl7.org/) and [Boston Children's Hospital](https://www.childrenshospital.org/).

---

© 2024–2026 dotimplement ai. HealthChain is an open source project maintained by [dotimplement ai](https://dotimplement.ai).

<!-- Badge Links -->

[pypi-version-badge]: https://img.shields.io/pypi/v/healthchain?logo=python&logoColor=white&style=flat-square&color=%23e59875
[downloads-badge]: https://img.shields.io/pepy/dt/healthchain?style=flat-square&color=%2379a8a9
[stars-badge]: https://img.shields.io/github/stars/healthchainai/HealthChain?style=flat-square&logo=github&color=BD932F&logoColor=white
[license-badge]: https://img.shields.io/github/license/healthchainai/HealthChain?style=flat-square&color=%23e59875
[python-versions-badge]: https://img.shields.io/pypi/pyversions/healthchain?style=flat-square&color=%23eeeeee
[build-badge]: https://img.shields.io/github/actions/workflow/status/healthchainai/healthchain/ci.yml?branch=main&style=flat-square&color=%2379a8a9
[discord-badge]: https://img.shields.io/badge/chat-%235965f2?style=flat-square&logo=discord&logoColor=white
[substack-badge]: https://img.shields.io/badge/Cool_Things_In_HealthTech-%23c094ff?style=flat-square&logo=substack&logoColor=white
[ai-badge]: https://img.shields.io/badge/AI--dev_friendly-CLAUDE.MD-%23e59875?style=flat-square&logo=anthropic&logoColor=white
[pypi]: https://pypi.org/project/healthchain/
[pypistats]: https://pepy.tech/project/healthchain
[stars]: https://github.com/healthchainai/HealthChain/stargazers
[license]: https://github.com/healthchainai/HealthChain/blob/main/LICENSE
[build]: https://github.com/healthchainai/HealthChain/actions?query=branch%3Amain
[discord]: https://discord.gg/UQC6uAepUz
[substack]: https://jenniferjiangkells.substack.com/
[claude-md]: CLAUDE.md
