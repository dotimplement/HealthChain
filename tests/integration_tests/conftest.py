"""Shared fixtures for integration tests."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from healthchain.gateway import NoteReaderService
from healthchain.gateway.cds import CDSHooksService
from healthchain.gateway.fhir import FHIRGateway
from healthchain.gateway.events.dispatcher import EventDispatcher
from healthchain.gateway import HealthChainAPI
from healthchain.pipeline.medicalcodingpipeline import MedicalCodingPipeline
from healthchain.pipeline.summarizationpipeline import SummarizationPipeline
from healthchain.fhir import create_document_reference
from fhir.resources.documentreference import DocumentReference
from fhir.resources.patient import Patient
from fhir.resources.meta import Meta


@pytest.fixture
def mock_coding_pipeline(test_cda_response):
    """Mock medical coding pipeline that returns test CDA response."""
    pipeline = MagicMock(spec=MedicalCodingPipeline)
    pipeline.process_request.return_value = test_cda_response
    return pipeline


@pytest.fixture
def mock_summarization_pipeline(test_cds_response_single_card):
    """Mock summarization pipeline that returns test CDS response."""
    pipeline = MagicMock(spec=SummarizationPipeline)
    pipeline.process_request.return_value = test_cds_response_single_card
    return pipeline


@pytest.fixture
def note_service(mock_coding_pipeline):
    """NoteReader service with mock pipeline."""
    service = NoteReaderService()

    @service.method("ProcessDocument")
    def process_document(cda_request):
        return mock_coding_pipeline.process_request(cda_request)

    return service


@pytest.fixture
def cds_service(mock_summarization_pipeline):
    """CDS Hooks service with mock pipeline."""
    service = CDSHooksService()

    @service.hook("encounter-discharge", id="discharge-summary")
    def handle_discharge_summary(request):
        return mock_summarization_pipeline.process_request(request)

    return service


@pytest.fixture
def fhir_gateway():
    """FHIR Gateway with transform and aggregate handlers."""
    gateway = FHIRGateway()

    @gateway.transform(DocumentReference)
    def enhance_document(id: str, source: str) -> DocumentReference:
        document = create_document_reference(
            data="AI-enhanced document",
            content_type="text/xml",
            description="Enhanced document",
        )
        document.extension = [
            {
                "url": "http://healthchain.org/extension/ai-summary",
                "valueString": "AI-enhanced",
            }
        ]
        document.meta = Meta(
            lastUpdated=datetime.now().isoformat(),
            tag=[{"system": "http://healthchain.org/tag", "code": "ai-enhanced"}],
        )
        return document

    @gateway.aggregate(Patient)
    def aggregate_patient_data(id: str, sources: list[str]) -> Patient:
        patient = Patient()
        patient.id = id
        patient.gender = "unknown"
        patient.birthDate = "1990-01-01"
        return patient

    return gateway


@pytest.fixture
def configured_app(note_service, cds_service, fhir_gateway):
    """HealthChainAPI with all services configured."""
    app = HealthChainAPI()
    app.register_service(note_service)
    app.register_service(cds_service)
    app.register_gateway(fhir_gateway)
    return app


@pytest.fixture
def event_dispatcher():
    """Event dispatcher for testing event system."""
    return EventDispatcher()


@pytest.fixture
def note_service_with_events(mock_coding_pipeline, event_dispatcher):
    """NoteReader service with event dispatching enabled."""
    service = NoteReaderService(event_dispatcher=event_dispatcher, use_events=True)

    @service.method("ProcessDocument")
    def process_document(cda_request):
        return mock_coding_pipeline.process_request(cda_request)

    return service


@pytest.fixture
def cds_service_with_events(mock_summarization_pipeline, event_dispatcher):
    """CDS Hooks service with event dispatching enabled."""
    service = CDSHooksService(event_dispatcher=event_dispatcher, use_events=True)

    @service.hook("encounter-discharge", id="discharge-summary")
    def handle_discharge_summary(request):
        return mock_summarization_pipeline.process_request(request)

    return service
