# 🍳 Cookbook: Hands-On Examples

Dive into real-world, production-ready examples to learn how to build interoperable healthcare AI apps with **HealthChain**.

---

## 🚦 Getting Started

- [**Working with FHIR Sandboxes**](./setup_fhir_sandboxes.md)
  *Spin up and access free Epic, Medplum, and other FHIR sandboxes for safe experimentation. This is the recommended first step before doing the detailed tutorials below.*

---

## 📚 How-To Guides

- 🔬 **[Deploy ML Models: Real-Time Alerts & Batch Screening](./ml_model_deployment.md)**
  *Deploy the same ML model two ways: CDS Hooks for point-of-care sepsis alerts, and FHIR Gateway for population-level batch screening with RiskAssessment resources.*

- 🚦 **[Multi-Source Patient Data Aggregation](./multi_ehr_aggregation.md)**
  *Merge patient data from multiple FHIR sources (Epic, Cerner, etc.), deduplicate conditions, prove provenance, and robustly handle cross-vendor errors. Foundation for retrieval-augmented generation (RAG) and analytics workflows.*

- 🧾 **[Automate Clinical Coding & FHIR Integration](./clinical_coding.md)**
  *Extract medical conditions from clinical documentation using AI, map to SNOMED CT codes, and sync as FHIR Condition resources to systems like Medplum—enabling downstream billing, analytics, and interoperability.*

- 📝 **[Summarize Discharge Notes with CDS Hooks](./discharge_summarizer.md)**
  *Deploy a CDS Hooks-compliant service that listens for discharge events, auto-generates concise plain-language summaries, and delivers actionable clinical cards directly into the EHR workflow.*

---

!!! info "What next?"
    See the source code for each recipe, experiment with the sandboxes, and adapt the patterns for your projects!
