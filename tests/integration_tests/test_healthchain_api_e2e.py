"""Integration tests for HealthChain API end-to-end workflows."""

from healthchain.models.requests.cdsrequest import CDSRequest


def test_notereader_service_processes_through_pipeline(
    note_service, test_cda_request, test_cda_response, mock_coding_pipeline
):
    """NoteReader service integrates with medical coding pipeline for document processing."""
    response = note_service.handle("ProcessDocument", request=test_cda_request)

    # Verify pipeline was invoked and response matches
    mock_coding_pipeline.process_request.assert_called_once_with(test_cda_request)
    assert response.document == test_cda_response.document


def test_cds_service_processes_through_pipeline(
    cds_service, test_cds_response_single_card, mock_summarization_pipeline
):
    """CDS Hooks service integrates with summarization pipeline for decision support."""
    cds_request = CDSRequest(
        hook="encounter-discharge",
        hookInstance="test",
        context={"patientId": "123", "userId": "Practitioner/1"},
    )

    response = cds_service.handle("encounter-discharge", request=cds_request)

    # Verify pipeline was invoked and cards generated
    mock_summarization_pipeline.process_request.assert_called_once_with(cds_request)
    assert len(response.cards) == 1
    assert response.cards[0].summary == test_cds_response_single_card.cards[0].summary


def test_fhir_gateway_supports_multiple_resource_operations(fhir_gateway):
    """FHIR Gateway handles both transform and aggregate operations on different resource types."""
    from fhir.resources.documentreference import DocumentReference
    from fhir.resources.patient import Patient

    # Transform operation
    doc = fhir_gateway._resource_handlers[DocumentReference]["transform"](
        "id1", "source1"
    )
    assert isinstance(doc, DocumentReference)
    assert doc.extension
    assert any("ai-summary" in ext.url for ext in doc.extension)

    # Aggregate operation
    patient = fhir_gateway._resource_handlers[Patient]["aggregate"]("id2", ["s1", "s2"])
    assert isinstance(patient, Patient)
    assert patient.id == "id2"


def test_healthchain_app_integrates_multiple_service_types(configured_app):
    """HealthChainAPI successfully orchestrates NoteReader, CDS Hooks, and FHIR Gateway services."""
    # Verify all service types are registered
    assert len(configured_app.services) == 2
    assert len(configured_app.gateways) == 1

    # Verify service types
    assert "NoteReaderService" in configured_app.services
    assert "CDSHooksService" in configured_app.services
    assert "FHIRGateway" in configured_app.gateways

    # Verify services are operational by checking they have required methods
    note_service = configured_app.services["NoteReaderService"]
    assert hasattr(note_service, "handle")

    cds_service = configured_app.services["CDSHooksService"]
    assert hasattr(cds_service, "handle")

    fhir_gateway = configured_app.gateways["FHIRGateway"]
    assert hasattr(fhir_gateway, "_resource_handlers")
