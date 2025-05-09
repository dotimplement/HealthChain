import pytest
from unittest.mock import MagicMock

from healthchain.sandbox.use_cases.cds import (
    CdsRequestConstructor,
    ClinicalDecisionSupport,
)
from healthchain.sandbox.workflows import Workflow, UseCaseType
from healthchain.models.hooks.prefetch import Prefetch
from healthchain.service.endpoints import ApiProtocol
from healthchain.fhir import create_bundle


def test_cds_request_constructor_init():
    """Test CdsRequestConstructor initialization"""
    constructor = CdsRequestConstructor()

    # Check protocol setting
    assert constructor.api_protocol == ApiProtocol.rest

    # Check context mapping
    assert Workflow.patient_view in constructor.context_mapping
    assert Workflow.order_select in constructor.context_mapping
    assert Workflow.order_sign in constructor.context_mapping
    assert Workflow.encounter_discharge in constructor.context_mapping


def test_cds_request_constructor_validation():
    """Test validation of workflows in CdsRequestConstructor"""
    constructor = CdsRequestConstructor()

    # Create a prefetch object
    prefetch = Prefetch(prefetch={"patient": create_bundle()})

    # Test with valid workflow
    valid_workflow = Workflow.patient_view
    # Should not raise error
    constructor.construct_request(prefetch_data=prefetch, workflow=valid_workflow)

    # Test with invalid workflow - should raise ValueError
    with pytest.raises(ValueError):
        # Not a real workflow
        invalid_workflow = MagicMock()
        invalid_workflow.value = "invalid-workflow"
        constructor.construct_request(prefetch_data=prefetch, workflow=invalid_workflow)


def test_cds_request_constructor_type_error():
    """Test type error handling in CdsRequestConstructor"""
    constructor = CdsRequestConstructor()

    # Test with invalid prefetch data type - should raise TypeError
    with pytest.raises(TypeError):
        # Not a Prefetch object
        invalid_prefetch = {"patient": create_bundle()}
        constructor.construct_request(
            prefetch_data=invalid_prefetch, workflow=Workflow.patient_view
        )


def test_cds_request_construction():
    """Test request construction in CdsRequestConstructor"""
    constructor = CdsRequestConstructor()

    # Create a bundle and prefetch
    bundle = create_bundle()
    prefetch = Prefetch(prefetch={"patient": bundle})

    # Construct a request
    request = constructor.construct_request(
        prefetch_data=prefetch,
        workflow=Workflow.patient_view,
        context={"patientId": "test-patient-123"},
    )

    # Verify request properties
    assert request.hook == "patient-view"
    assert request.context.patientId == "test-patient-123"
    assert request.prefetch == prefetch.prefetch


def test_clinical_decision_support_init():
    """Test ClinicalDecisionSupport initialization"""
    # Test with default parameters
    cds = ClinicalDecisionSupport()
    assert cds.type == UseCaseType.cds
    assert isinstance(cds.strategy, CdsRequestConstructor)
    assert cds._path == "/cds-services/"

    # Test with custom path
    custom_path = "/api/cds/"
    cds_custom = ClinicalDecisionSupport(path=custom_path)
    assert cds_custom._path == custom_path


def test_clinical_decision_support_properties():
    """Test ClinicalDecisionSupport properties"""
    cds = ClinicalDecisionSupport()

    # Check properties
    assert cds.description == "Clinical decision support (HL7 CDS specification)"
    assert cds.type == UseCaseType.cds
    assert isinstance(cds.strategy, CdsRequestConstructor)
