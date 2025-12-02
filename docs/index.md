# Welcome to HealthChain 💫 🏥

HealthChain is an open-source Python toolkit that streamlines productionizing healthcare AI. Built for AI/ML practitioners, it simplifies the complexity of real-time EHR integrations by providing seamless FHIR integration, unified data pipelines, and production-ready deployment.

[ :fontawesome-brands-discord: Join our Discord](https://discord.gg/UQC6uAepUz){ .md-button .md-button--primary }
&nbsp;&nbsp;&nbsp;&nbsp;
[ :octicons-rocket-24: Quickstart Guide](quickstart.md){ .md-button .md-button--secondary }

## What are the main features?

<div class="grid cards" markdown>

-   :material-tools:{ .lg .middle } __FHIR-native Pipelines__

    ---

    Create custom pipelines or use pre-built ones for healthcare NLP and ML tasks with automatic FHIR output

    [:octicons-arrow-right-24: Pipeline](reference/pipeline/pipeline.md)

-   :material-connection:{ .lg .middle } __Multi-EHR Gateway__

    ---

    Connect to multiple healthcare systems with unified API supporting FHIR, CDS Hooks, and SOAP/CDA protocols

    [:octicons-arrow-right-24: Gateway](reference/gateway/gateway.md)

-   :material-database:{ .lg .middle } __Healthcare Data Conversion__

    ---

    Convert between FHIR, CDA, and HL7v2 formats using configuration-driven InteropEngine

    [:octicons-arrow-right-24: Interoperability](reference/interop/interop.md)

-   :material-fire:{ .lg .middle } __Developer Utilities__

    ---

    Type-safe FHIR resources, validation helpers, and sandbox environments for rapid development

    [:octicons-arrow-right-24: Utilities](reference/utilities/fhir_helpers.md)

</div>

## Getting Started with Healthcare AI

HealthChain provides the missing middleware layer between healthcare systems and modern AI/ML development. Whether you're building clinical decision support tools, processing medical documents, or creating multi-system integrations, these docs will guide you through:

- **🔧 Core concepts** - Understand FHIR resources, pipelines, and gateway patterns
- **📚 Real examples** - Step-by-step tutorials for common healthcare AI use cases
- **🏗️ Advanced patterns** - Production deployment, authentication, and multi-EHR workflows
- **🧪 Testing tools** - Sandbox environments and utilities for development

## What You Can Build with HealthChain

|   | Use Case                              | Description                                                                 |
|---|---------------------------------------|-----------------------------------------------------------------------------|
| 🚨 | **CDS alerts for discharge summaries** | Generate clinical recommendations directly in Epic workflows                |
| 📋 | **Automatic medical coding**          | Extract ICD-10 or SNOMED-CT codes from physician notes with confidence scores|
| 🔗 | **Multi-EHR patient aggregation**     | Combine patient records from Epic, Cerner, and specialty systems            |
| 🤖 | **ML model deployment**               | Serve your trained healthcare models as FHIR-compliant APIs                 |
| 🔄 | **Legacy document conversion**        | Transform CDA documents to modern FHIR resources                            |

**New to healthcare AI?** Start with our [Quickstart Guide](quickstart.md) to build your first medical NLP pipeline in under 10 minutes.

**Ready to integrate with EHRs?** Jump to our [Cookbook](cookbook/index.md) for complete examples including CDS Hooks and FHIR integration.

---

HealthChain is made by a small team with experience in software engineering, machine learning, and healthcare NLP. We understand that good data science is about more than just building models, and that good engineering is about more than just building systems. This rings especially true in healthcare, where people, processes, and technology all play a role in making an impact.

For inquiries and collaborations, please get [in touch](mailto:jenniferjiangkells@gmail.com)!
