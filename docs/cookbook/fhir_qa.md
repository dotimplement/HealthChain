# FHIR-Grounded Patient Q&A

**Level:** Beginner

This example shows you how to build a Q&A service that answers patient questions using their live clinical data as context. The service fetches FHIR resources from a connected EHR, formats them into a structured prompt context using a HealthChain pipeline, and passes both to an LLM to generate a grounded, personalised response.

This is the foundational pattern for patient-facing AI assistants — hospital portal chatbots, discharge navigation tools, care plan Q&A — where answers must be anchored to the individual patient's record rather than general medical knowledge.

Check out the full working example [here](https://github.com/dotimplement/HealthChain/tree/main/cookbook/fhir_context_llm_qa.py)!

## Setup

```bash
pip install healthchain langchain-core langchain-anthropic python-dotenv

# or for HuggingFace models
pip install healthchain langchain-core langchain-huggingface python-dotenv
```

We'll use [Medplum](https://www.medplum.com/) as our FHIR sandbox — it lets you seed your own synthetic patients and query them over a standard FHIR R4 API. If you haven't set up Medplum access yet, see the [FHIR Sandbox Setup Guide](./setup_fhir_sandboxes.md#medplum) for step-by-step instructions.

Once you have your Medplum credentials, add them to a `.env` file:

```bash
# .env file
MEDPLUM_CLIENT_ID=your_client_id
MEDPLUM_CLIENT_SECRET=your_client_secret
MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4
MEDPLUM_TOKEN_URL=https://api.medplum.com/oauth2/token
ANTHROPIC_API_KEY=your_api_key   # or OPENAI_API_KEY, etc.
```

### Seed test data

The cookbook ships with a demo patient bundle — a synthetic patient with a condition, an upcoming appointment, and an active care plan. Upload it to your Medplum instance with:

```bash
healthchain seed medplum ./cookbook/data/qa_patient.json
```

Note the printed patient ID — you'll use it when testing the `/qa` endpoint:

```
✓ DEMO_PATIENT_ID=<id>
```

## Format FHIR data as LLM context

The first piece is a HealthChain [Pipeline](../reference/pipeline/pipeline.md) that transforms a FHIR Bundle into a structured plain-text context block. This is a deliberate design choice: the LLM never sees raw FHIR JSON. Instead, you control exactly what clinical information is surfaced and how it's phrased.

```python
from healthchain.pipeline import Pipeline
from healthchain.io.containers import Document

def create_pipeline() -> Pipeline[Document]:
    pipeline = Pipeline[Document]()

    @pipeline.add_node
    def format_context(doc: Document) -> Document:
        conditions = doc.fhir.get_resources("Condition")
        appointments = doc.fhir.get_resources("Appointment")
        careplans = doc.fhir.get_resources("CarePlan")

        lines = ["PATIENT CLINICAL CONTEXT"]
        if conditions:
            lines.append("\nDiagnoses:")
            for c in conditions:
                onset = c.onsetDateTime
                lines.append(
                    f"  - {c.code.text}" + (f" (since {onset})" if onset else "")
                )
        if appointments:
            lines.append("\nUpcoming Appointments:")
            for a in appointments:
                lines.append(f"  - {a.description}: {a.start}")
        if careplans:
            lines.append("\nCare Plan:")
            for cp in careplans:
                lines.append(f"  {cp.description}")

        doc.text = "\n".join(lines)
        return doc

    return pipeline
```

When you initialize a [Document](../reference/io/containers/document.md) with a FHIR Bundle, it automatically extracts resources by type so you can query them directly:

```python
doc = Document(data=bundle)

doc.fhir.get_resources("Condition")    # List[Condition]
doc.fhir.get_resources("Appointment")  # List[Appointment]
doc.fhir.get_resources("CarePlan")     # List[CarePlan]
```

After the pipeline runs, `doc.text` holds the formatted context string ready to inject into the LLM prompt.

!!! tip "Customising context"

    What you include here directly shapes response quality. Common additions:
    
    - **Medications** — `doc.fhir.get_resources("MedicationRequest")`
    - **Recent results** — `doc.fhir.get_resources("Observation")`
    - **Discharge letters** — `doc.fhir.get_resources("DocumentReference")`
    
    For sensitive resources (mental health, substance use), apply consent-based filtering before adding them to context.

## Build the Q&A chain

The second piece is a LangChain chain that takes the formatted context and the patient's question and returns a grounded answer. The system prompt sets the scope: answer from the patient's record, don't provide medical diagnoses, refer clinical questions to the care team.

```python
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

def create_chain(llm: BaseChatModel):
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a patient information assistant at a hospital. "
                "Use the patient's clinical context to give accurate, personalised responses. "
                "Do not provide medical advice or diagnoses. "
                "Refer clinical questions to the care team.",
            ),
            ("human", "{context}\n\nPatient question: {question}"),
        ]
    )
    return prompt | llm | StrOutputParser()
```

Any LangChain-compatible LLM works here — swap `ChatAnthropic` for a HuggingFace model or any other provider without changing the pipeline or gateway:

```python
from langchain_huggingface.llms import HuggingFaceEndpoint
from langchain_huggingface import ChatHuggingFace

hf = HuggingFaceEndpoint(
    repo_id="mistralai/Mistral-7B-Instruct-v0.3",
    task="text-generation",
    max_new_tokens=512,
)
llm = ChatHuggingFace(llm=hf)
app = create_app(llm)
```

Set `HUGGINGFACEHUB_API_TOKEN` in your `.env` file to authenticate.

!!! note "HealthChain complements your existing stack"

    HealthChain handles the healthcare-specific plumbing: FHIR authentication, resource fetching, context formatting, and deployment scaffolding. Your LangChain chains, prompts, and LLM choices stay exactly as they are. If you're already using FastAPI, `HealthChainAPI` is a thin wrapper that adds FHIR-aware routing and auto-generated OpenAPI docs on top — you're not replacing anything.

## Build the service

Wire the gateway, pipeline, and chain together into a [HealthChainAPI](../reference/gateway/api.md) service with a single `/qa` endpoint:

```python
from pydantic import BaseModel
from healthchain.fhir.r4b import Condition, Appointment, CarePlan
from healthchain.gateway import FHIRGateway, HealthChainAPI
from healthchain.gateway.clients import FHIRAuthConfig
from healthchain.fhir import merge_bundles

class PatientQuestion(BaseModel):
    patient_id: str
    question: str

class PatientAnswer(BaseModel):
    patient_id: str
    question: str
    answer: str

def create_app(llm: BaseChatModel) -> HealthChainAPI:
    fhir_config = FHIRAuthConfig.from_env("MEDPLUM")
    gateway = FHIRGateway()
    gateway.add_source("medplum", fhir_config.to_connection_string())

    pipeline = create_pipeline()
    chain = create_chain(llm)

    app = HealthChainAPI(
        title="FHIR-Grounded Patient Q&A",
        description="Answers patient questions using live FHIR data as context",
        service_type="fhir-gateway",
    )

    @app.post("/qa")
    def answer_question(request: PatientQuestion) -> PatientAnswer:
        bundles = []
        for resource_type in [Condition, Appointment, CarePlan]:
            try:
                bundle = gateway.search(
                    resource_type, {"patient": request.patient_id}, "medplum"
                )
                bundles.append(bundle)
            except Exception as e:
                print(f"Warning: Could not fetch {resource_type.__name__}: {e}")

        doc = Document(data=merge_bundles(bundles))
        doc = pipeline(doc)

        answer = chain.invoke({"context": doc.text, "question": request.question})
        return PatientAnswer(
            patient_id=request.patient_id,
            question=request.question,
            answer=answer,
        )

    return app
```

Then run it:

```python
from langchain_anthropic import ChatAnthropic

if __name__ == "__main__":
    llm = ChatAnthropic(model="claude-opus-4-6", max_tokens=512)
    app = create_app(llm)
    app.run(port=8888)
```

!!! info "How the endpoint works"

    For each `/qa` request, the service:
    
    1. Fetches Conditions, Appointments, and CarePlans for the patient from Medplum
    2. Merges them into a single Bundle with `merge_bundles()`
    3. Runs the pipeline to produce a plain-text context string
    4. Calls the LLM chain with the context + question
    5. Returns the answer as a `PatientAnswer` JSON response

## Test the service

With the service running at `http://localhost:8888`, use your seeded patient ID from `.env`:

=== "cURL"
    ```bash
    curl -X POST http://localhost:8888/qa \
      -H "Content-Type: application/json" \
      -d '{"patient_id": "<DEMO_PATIENT_ID>", "question": "When is my next appointment?"}'
    ```

=== "Python"
    ```python
    import requests

    response = requests.post(
        "http://localhost:8888/qa",
        json={
            "patient_id": "<DEMO_PATIENT_ID>",
            "question": "When is my next appointment?",
        },
    )
    print(response.json())
    ```

Interactive API docs are available at `http://localhost:8888/docs`.

??? example "Illustrative response"

    ```json
    {
      "patient_id": "abc123",
      "question": "When is my next appointment?",
      "answer": "Your next appointment is a Colposcopy follow-up scheduled for 10 April 2026 at 10:00 AM. If you need to reschedule or have questions about what to expect, please contact your care team directly."
    }
    ```

    *Output will vary based on your seeded patient data and LLM model.*

??? warning "Missing resources"

    If a resource type isn't available for a patient, the service logs a warning and continues — partial context is better than an error:

    ```
    Warning: Could not fetch CarePlan: [FHIR request failed: 404]
    ```

    The LLM will answer based on whatever resources were successfully retrieved.

## What You've Built

A FHIR-grounded patient Q&A service that:

- **Fetches live FHIR data** — connects to any FHIR R4 server via the gateway; swap Medplum for Epic, Cerner, or an NHS API by changing the source config
- **Formats context deterministically** — the pipeline controls exactly what the LLM sees; no raw FHIR JSON in prompts
- **Is LLM-agnostic** — any LangChain-compatible model works without changing the pipeline or gateway
- **Handles partial data gracefully** — individual resource failures don't crash the service
- **Exposes a standard REST endpoint** — auto-documented at `/docs`, ready to call from a frontend or other service

!!! info "Use Cases"

    - **Patient portal chatbots** — answer "what medications am I on?", "when is my next scan?", "what does my care plan say?" directly from the patient's record
    - **Discharge navigation** — help patients understand their discharge instructions, follow-up appointments, and care plan actions in plain language
    - **Clinical inbox triage** — pre-generate context-aware responses to common patient messages, reducing administrative burden on care teams
    - **Care plan explanation** — surface care plan steps in patient-friendly language, personalised to their conditions and appointments

!!! tip "Next Steps"

    - **Add more resource types**: Extend the pipeline to include `MedicationRequest`, `Observation`, or `DocumentReference` for richer context
    - **Swap the LLM**: Replace `ChatAnthropic` with a HuggingFace model (`ChatHuggingFace` + `HuggingFaceEndpoint`) or any other LangChain-compatible provider — the pipeline and gateway are unchanged
    - **Connect to a real FHIR source**: Replace Medplum with an Epic or Cerner sandbox — see [Setup FHIR Sandboxes](./setup_fhir_sandboxes.md) for instructions
    - **Add conversation history**: Extend `PatientQuestion` with a `history` field and pass it into the LangChain prompt for multi-turn Q&A
    - **Go to production**: Scaffold a project with `healthchain new` and run with `healthchain serve` — see [From cookbook to service](./index.md#from-cookbook-to-service). Moving to `healthchain.yaml` is where config-driven compliance support (audit logging, certificates, deployment metadata) will live as those features mature.
