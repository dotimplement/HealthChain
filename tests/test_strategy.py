import pytest

from unittest.mock import patch, MagicMock
from healthchain.workflows import Workflow
from healthchain.models import CDSRequest
from healthchain.models.hooks import (
    PatientViewContext,
    OrderSelectContext,
    OrderSignContext,
    EncounterDischargeContext,
)
from healthchain.models import CdaRequest
from healthchain.use_cases.clindoc import ClinicalDocumentationStrategy
from healthchain.service.endpoints import ApiProtocol


def test_strategy_configuration(cds_strategy):
    """Test basic strategy configuration."""
    # Test API protocol
    assert cds_strategy.api_protocol == ApiProtocol.rest

    # Test context mapping completeness
    expected_mappings = {
        Workflow.order_select: OrderSelectContext,
        Workflow.order_sign: OrderSignContext,
        Workflow.patient_view: PatientViewContext,
        Workflow.encounter_discharge: EncounterDischargeContext,
    }
    assert cds_strategy.context_mapping == expected_mappings
    assert all(
        workflow in cds_strategy.context_mapping for workflow in expected_mappings
    )


def test_valid_request_construction(cds_strategy, valid_prefetch_data):
    """Test construction of valid requests with different context types."""
    # Test PatientViewContext
    with patch.object(CDSRequest, "__init__", return_value=None) as mock_init:
        cds_strategy.construct_request(
            prefetch_data=valid_prefetch_data,
            workflow=Workflow.patient_view,
            context={"userId": "Practitioner/123", "patientId": "123"},
        )
        mock_init.assert_called_once_with(
            hook=Workflow.patient_view.value,
            context=PatientViewContext(userId="Practitioner/123", patientId="123"),
            prefetch=valid_prefetch_data,
        )

    # # Test OrderSelectContext
    # order_select_result = cds_strategy.construct_request(
    #     prefetch_data=valid_prefetch_data,
    #     workflow=Workflow.order_select,
    #     context={"userId": "Practitioner/123", "patientId": "123", "selections": []},
    # )
    # assert isinstance(order_select_result.context, OrderSelectContext)

    # Test EncounterDischargeContext
    discharge_result = cds_strategy.construct_request(
        prefetch_data=valid_prefetch_data,
        workflow=Workflow.encounter_discharge,
        context={
            "userId": "Practitioner/123",
            "patientId": "123",
            "encounterId": "456",
        },
    )
    assert isinstance(discharge_result.context, EncounterDischargeContext)


def test_context_mapping_behavior(cds_strategy, valid_prefetch_data):
    """Test context mapping functionality."""
    with patch.dict(
        cds_strategy.context_mapping,
        {
            Workflow.patient_view: MagicMock(
                spec=PatientViewContext,
                return_value=PatientViewContext(
                    userId="Practitioner/123", patientId="123"
                ),
            )
        },
    ):
        cds_strategy.construct_request(
            prefetch_data=valid_prefetch_data,
            workflow=Workflow.patient_view,
            context={"userId": "Practitioner/123", "patientId": "123"},
        )
        cds_strategy.context_mapping[Workflow.patient_view].assert_called_once_with(
            userId="Practitioner/123", patientId="123"
        )


def test_error_handling(cds_strategy, valid_prefetch_data):
    """Test various error conditions in request construction."""
    # Test invalid context keys
    with pytest.raises(ValueError):
        cds_strategy.construct_request(
            prefetch_data={},
            workflow=Workflow.patient_view,
            context={"invalidId": "Practitioner", "patientId": "123"},
        )

    # Test missing required context data
    with pytest.raises(ValueError):
        cds_strategy.construct_request(
            prefetch_data={},
            workflow=Workflow.patient_view,
            context={"userId": "Practitioner"},
        )

    # Test invalid prefetch data type
    invalid_prefetch = {"patient": {"id": "123"}}  # Not a FHIR Resource
    with pytest.raises(TypeError) as excinfo:
        cds_strategy.construct_request(
            prefetch_data=invalid_prefetch,
            workflow=Workflow.patient_view,
            context={"userId": "Practitioner/123", "patientId": "123"},
        )
    assert "not a valid FHIR resource" in str(excinfo.value)

    # Test unsupported workflow
    mock_workflow = MagicMock()
    mock_workflow.value = "unsupported-workflow"
    with pytest.raises(ValueError) as excinfo:
        cds_strategy.construct_request(
            prefetch_data=valid_prefetch_data,
            workflow=mock_workflow,
            context={"userId": "Practitioner/123", "patientId": "123"},
        )
    assert "Invalid workflow" in str(excinfo.value)


def test_workflow_validation(cds_strategy, valid_prefetch_data):
    """Test workflow validation decorator behavior."""
    # Test invalid workflow
    with pytest.raises(ValueError) as excinfo:
        cds_strategy.construct_request(
            prefetch_data=valid_prefetch_data,
            workflow=Workflow.sign_note_inpatient,
            context={"userId": "Practitioner/123", "patientId": "123"},
        )
    assert "Invalid workflow" in str(excinfo.value)

    # Test valid workflow
    result = cds_strategy.construct_request(
        prefetch_data={},
        workflow=Workflow.patient_view,
        context={"userId": "Practitioner/123", "patientId": "123"},
    )
    assert isinstance(result, CDSRequest)
    assert result.prefetch == {}


def test_cda_request_construction(
    doc_ref_with_cda_xml, doc_ref_with_multiple_content, caplog
):
    """Test CDA-specific request construction."""
    strategy = ClinicalDocumentationStrategy()
    workflow = Workflow.sign_note_inpatient

    # Test with valid CDA XML
    request = strategy.construct_request(doc_ref_with_cda_xml, workflow)
    assert isinstance(request, CdaRequest)
    assert request.document is not None
    assert "urn:Document" in request.document

    # Test with non-CDA content
    strategy.construct_request(doc_ref_with_multiple_content, workflow)
    assert "No CDA document found in the DocumentReference!" in caplog.text
