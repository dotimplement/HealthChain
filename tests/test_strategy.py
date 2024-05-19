import pytest

from unittest.mock import patch, MagicMock
from healthchain.base import Workflow
from healthchain.models.requests.cdsrequest import CDSRequest

from healthchain.models.hooks.patientview import PatientViewContext


def test_valid_data_request_construction(cds_strategy, valid_data):
    with patch.object(CDSRequest, "__init__", return_value=None) as mock_init:
        cds_strategy.construct_request(valid_data, Workflow.patient_view)
        mock_init.assert_called_once_with(
            hook=Workflow.patient_view.value,
            context=PatientViewContext(userId="Practitioner/123", patientId="123"),
            prefetch={"condition": "test"},
        )


def test_invalid_data_raises_error(cds_strategy, invalid_data):
    with pytest.raises(ValueError):
        # incorrect keys passed in
        cds_strategy.construct_request(invalid_data, Workflow.patient_view)

    with pytest.raises(ValueError):
        # correct keys but invalid data
        invalid_data.context = {"userId": "Practitioner"}
        cds_strategy.construct_request(invalid_data, Workflow.patient_view)


def test_context_mapping(cds_strategy, valid_data):
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
        cds_strategy.construct_request(data=valid_data, workflow=Workflow.patient_view)
        cds_strategy.context_mapping[Workflow.patient_view].assert_called_once_with(
            **valid_data.context
        )


def test_workflow_validation_decorator(cds_strategy, valid_data):
    with pytest.raises(ValueError) as excinfo:
        cds_strategy.construct_request(Workflow.notereader_sign_inpatient, valid_data)
    assert "Invalid workflow" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        cds_strategy.construct_request(
            data=valid_data, workflow=Workflow.notereader_sign_inpatient
        )
    assert "Invalid workflow" in str(excinfo.value)

    assert cds_strategy.construct_request(valid_data, Workflow.patient_view)
