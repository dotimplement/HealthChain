#!/usr/bin/env python3
"""
FHIR-Grounded Patient Q&A

Pulls patient data from a FHIR store, formats it as context, and serves
a Q&A endpoint powered by any LangChain-compatible LLM.

Requirements:
    pip install healthchain langchain-core langchain-anthropic python-dotenv

Setup:
    1. Add to .env:
           MEDPLUM_CLIENT_ID=your_client_id
           MEDPLUM_CLIENT_SECRET=your_client_secret
           MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4
           MEDPLUM_TOKEN_URL=https://api.medplum.com/oauth2/token
           ANTHROPIC_API_KEY=your_api_key   # or OPENAI_API_KEY, etc.
    2. Seed demo patient:
           healthchain seed medplum ./cookbook/data/qa_patient.json
       Note the printed DEMO_PATIENT_ID for use when testing.

Run:
    python cookbook/fhir_context_llm_qa.py
    # Starts a service and keeps running for interactive use.
    # POST /qa  {"patient_id": "...", "question": "..."}
    # Docs at: http://localhost:8888/docs
"""

from dotenv import load_dotenv
from pydantic import BaseModel

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic

from healthchain.fhir.r4b import Condition, Appointment, CarePlan

from healthchain.gateway import FHIRGateway, HealthChainAPI
from healthchain.gateway.clients import FHIRAuthConfig
from healthchain.pipeline import Pipeline
from healthchain.io.containers import Document
from healthchain.fhir import merge_bundles


load_dotenv()


class PatientQuestion(BaseModel):
    patient_id: str
    question: str


class PatientAnswer(BaseModel):
    patient_id: str
    question: str
    answer: str


def create_pipeline() -> Pipeline[Document]:
    """Format a FHIR patient bundle into a structured LLM context string."""
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


def create_chain(llm: BaseChatModel):
    """Q&A chain: patient context + question → grounded answer."""
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


if __name__ == "__main__":
    llm = ChatAnthropic(model="claude-opus-4-6", max_tokens=512)
    app = create_app(llm)
    app.run(port=8888)
