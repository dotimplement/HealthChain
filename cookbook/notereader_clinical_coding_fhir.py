#!/usr/bin/env python3
"""
A complete CDI service that processes clinical notes and extracts billing codes.
Demonstrates FHIR-native pipelines, legacy system integration, and multi-source data handling.

Requirements:
- pip install healthchain
- pip install scispacy
- pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
- pip install python-dotenv

Run:
- python notereader_clinical_coding_fhir.py  # Demo and start server
"""

import os
import uvicorn
from datetime import datetime, timezone

import healthchain as hc
from fhir.resources.documentreference import DocumentReference
from fhir.resources.meta import Meta
from spacy.tokens import Span
from dotenv import load_dotenv

from healthchain.fhir import create_document_reference
from healthchain.gateway.api import HealthChainAPI
from healthchain.gateway.fhir import FHIRGateway
from healthchain.gateway.soap import NoteReaderService
from healthchain.io import CdaAdapter, Document
from healthchain.models import CdaRequest
from healthchain.pipeline.medicalcodingpipeline import MedicalCodingPipeline
from healthchain.sandbox.use_cases import ClinicalDocumentation


load_dotenv()


BILLING_URL = (
    f"fhir://api.medplum.com/fhir/R4/"
    f"?client_id={os.environ.get('MEDPLUM_CLIENT_ID')}"
    f"&client_secret={os.environ.get('MEDPLUM_CLIENT_SECRET')}"
    f"&token_url={os.environ.get('MEDPLUM_TOKEN_URL', 'https://api.medplum.com/oauth2/token')}"
    f"&scope={os.environ.get('MEDPLUM_SCOPE', 'openid')}"
)


def create_pipeline():
    """Build FHIR-native ML pipeline with automatic problem extraction."""
    pipeline = MedicalCodingPipeline.from_model_id("en_core_sci_sm", source="spacy")

    # Add custom entity linking
    @pipeline.add_node(position="after", reference="SpacyNLP")
    def link_entities(doc: Document) -> Document:
        """Add CUI codes to medical entities for problem extraction"""
        if not Span.has_extension("cui"):
            Span.set_extension("cui", default=None)

        spacy_doc = doc.nlp.get_spacy_doc()

        # Simple dummy linker for demo purposes
        dummy_linker = {
            "pneumonia": "233604007",
            "type 2 diabetes mellitus": "44054006",
            "congestive heart failure": "42343007",
            "chronic kidney disease": "431855005",
            "hypertension": "38341003",
            "community acquired pneumonia": "385093006",
            "ventilator associated pneumonia": "233717007",
            "anaphylaxis": "39579001",
            "delirium": "2776000",
            "depression": "35489007",
            "asthma": "195967001",
            "copd": "13645005",
        }

        for ent in spacy_doc.ents:
            if ent.text.lower() in dummy_linker:
                ent._.cui = dummy_linker[ent.text.lower()]

        return doc

    return pipeline


def create_app():
    """Create production healthcare API."""
    pipeline = create_pipeline()
    cda_adapter = CdaAdapter()

    # Modern FHIR sources
    fhir_gateway = FHIRGateway()
    fhir_gateway.add_source("billing", BILLING_URL)

    # Legacy CDA processing
    note_service = NoteReaderService()

    @note_service.method("ProcessDocument")
    def ai_coding_workflow(request: CdaRequest):
        doc = cda_adapter.parse(request)
        doc = pipeline(doc)

        for condition in doc.fhir.problem_list:
            # Add basic provenance tracking
            condition.meta = Meta(
                source="urn:healthchain:pipeline:cdi",
                lastUpdated=datetime.now(timezone.utc).isoformat(),
            )
            fhir_gateway.create(condition, source="billing")

        cda_response = cda_adapter.format(doc)

        return cda_response

    # Register services
    app = HealthChainAPI(title="Epic CDI Service with FHIR integration")
    app.register_gateway(fhir_gateway, path="/fhir")
    app.register_service(note_service, path="/notereader")

    return app


def create_sandbox():
    @hc.sandbox(api="http://localhost:8000/")
    class NotereaderSandbox(ClinicalDocumentation):
        """Sandbox for testing clinical documentation workflows"""

        def __init__(self):
            super().__init__()
            self.data_path = "./resources/uclh_cda.xml"

        @hc.ehr(workflow="sign-note-inpatient")
        def load_clinical_document(self) -> DocumentReference:
            """Load a sample CDA document for processing"""
            with open(self.data_path, "r") as file:
                xml_content = file.read()

            return create_document_reference(
                data=xml_content,
                content_type="text/xml",
                description="Sample CDA document from sandbox",
            )

    return NotereaderSandbox()


# Create the app
app = create_app()


if __name__ == "__main__":
    import threading
    from time import sleep

    # Start server
    def run_server():
        uvicorn.run(app, port=8000, log_level="warning")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    sleep(2)  # Wait for startup

    # Test sandbox
    sandbox = create_sandbox()
    sandbox.start_sandbox()

    try:
        server_thread.join()
    except KeyboardInterrupt:
        pass
