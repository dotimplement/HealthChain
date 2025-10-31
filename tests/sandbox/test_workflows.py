"""Tests for sandbox workflow validation and mapping logic."""

import pytest

from healthchain.sandbox.workflows import (
    Workflow,
    UseCaseMapping,
    is_valid_workflow,
    validate_workflow,
)


def test_workflow_use_case_mapping_rules():
    """Workflow-UseCase mapping enforces correct associations."""
    # CDS workflows
    assert is_valid_workflow(
        UseCaseMapping.ClinicalDecisionSupport, Workflow.patient_view
    )
    assert is_valid_workflow(
        UseCaseMapping.ClinicalDecisionSupport, Workflow.order_select
    )
    assert is_valid_workflow(
        UseCaseMapping.ClinicalDecisionSupport, Workflow.encounter_discharge
    )

    # ClinDoc workflows
    assert is_valid_workflow(
        UseCaseMapping.ClinicalDocumentation, Workflow.sign_note_inpatient
    )
    assert is_valid_workflow(
        UseCaseMapping.ClinicalDocumentation, Workflow.sign_note_outpatient
    )

    # Invalid associations
    assert not is_valid_workflow(
        UseCaseMapping.ClinicalDocumentation, Workflow.patient_view
    )
    assert not is_valid_workflow(
        UseCaseMapping.ClinicalDecisionSupport, Workflow.sign_note_inpatient
    )


def test_validate_workflow_decorator_enforcement():
    """validate_workflow decorator rejects invalid workflow-usecase combinations."""

    @validate_workflow(UseCaseMapping.ClinicalDecisionSupport)
    def cds_function(data, workflow: Workflow):
        return f"Processing {workflow.value}"

    # Valid workflow passes
    result = cds_function("data", workflow=Workflow.patient_view)
    assert result == "Processing patient-view"

    # Invalid workflow raises ValueError
    with pytest.raises(ValueError, match="Invalid workflow .* for UseCase"):
        cds_function("data", workflow=Workflow.sign_note_inpatient)


def test_validate_workflow_decorator_with_positional_args():
    """validate_workflow decorator handles positional workflow arguments."""

    @validate_workflow(UseCaseMapping.ClinicalDocumentation)
    def clindoc_function(data, workflow: Workflow):
        return workflow.value

    # Positional argument
    result = clindoc_function("data", Workflow.sign_note_outpatient)
    assert result == "sign-note-outpatient"

    # Invalid positional argument
    with pytest.raises(ValueError, match="Invalid workflow"):
        clindoc_function("data", Workflow.order_select)
