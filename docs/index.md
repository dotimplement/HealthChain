# Welcome to HealthChain 💫 🏥

HealthChain is an open-source Python framework for building real-time AI applications in a healthcare context.

[ :fontawesome-brands-discord: Join our Discord](https://discord.gg/UQC6uAepUz){ .md-button .md-button--primary }
&nbsp;&nbsp;&nbsp;&nbsp;
[ :octicons-rocket-24: Quickstart Guide](quickstart.md){ .md-button .md-button--secondary }

## What are the main features?

<div class="grid cards" markdown>


-   :material-tools:{ .lg .middle } __Build a pipeline__

    ---

    Create custom pipelines or use pre-built ones for your healthcare NLP and ML tasks

    [:octicons-arrow-right-24: Pipeline](reference/pipeline/pipeline.md)

-   :material-connection:{ .lg .middle } __Connect to multiple data sources__

    ---

    Connect to multiple healthcare data sources and protocols with **HealthChainAPI**.

    [:octicons-arrow-right-24: Gateway](reference/gateway/gateway.md)

-   :material-database:{ .lg .middle } __Interoperability__

    ---

    Configuration-driven **InteropEngine** to convert between FHIR, CDA, and HL7v2

    [:octicons-arrow-right-24: Interoperability](reference/interop/interop.md)

-   :material-fire:{ .lg .middle } __Utilities__

    ---

    FHIR data model utilities and helpers to make development easier

    [:octicons-arrow-right-24: Utilities](reference/utilities/fhir_helpers.md)



</div>

## Why HealthChain?

Healthcare AI development has a **missing middleware layer**. Traditional enterprise integration engines move data around, EHR platforms serve end users, but there's nothing in between for developers building AI applications that need to talk to multiple healthcare systems. Few solutions are open-source, and even fewer are built in modern Python where most ML/AI libraries thrive.

HealthChain fills that gap with:

- **🔥 FHIR-native ML pipelines** - Pre-built NLP/ML pipelines optimized for structured / unstructured healthcare data, or build your own with familiar Python libraries such as 🤗 Hugging Face, 🤖 LangChain, and 📚 spaCy
- **🔒 Type-safe healthcare data** - Full type hints and Pydantic validation for FHIR resources with automatic data validation and error handling
- **🔌 Multi-protocol connectivity** - Handle FHIR, CDS Hooks, and SOAP/CDA in the same codebase with OAuth2 authentication and connection pooling
- **⚡ Event-driven architecture** - Real-time event handling with audit trails and workflow automation built-in
- **🔄 Built-in interoperability** - Convert between FHIR, CDA, and HL7v2 using a template-based engine
- **🚀 Production-ready deployment** - FastAPI integration for scalable, real-time applications

HealthChain is made by a small team with experience in software engineering, machine learning, and healthcare NLP. We understand that good data science is about more than just building models, and that good engineering is about more than just building systems. This rings especially true in healthcare, where people, processes, and technology all play a role in making an impact.

For inquiries and collaborations, please get [in touch](mailto:jenniferjiangkells@gmail.com)!
