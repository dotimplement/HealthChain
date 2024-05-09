import pytest
import dataclasses

from unittest.mock import patch, MagicMock
from healthchain.base import Workflow
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.use_cases.cds import ClinicalDecisionSupport
from healthchain.models.hooks.patientview import PatientViewContext


@dataclasses.dataclass
class synth_data:
    context: dict
    uuid: str
    prefetch: dict


@pytest.fixture
def cds():
    return ClinicalDecisionSupport()


@pytest.fixture
def valid_data():
    return synth_data(
        context={"userId": "Practitioner/123", "patientId": "123"},
        uuid="1234-5678",
        prefetch={},
    )


@pytest.fixture
def invalid_data():
    return synth_data(
        context={"invalidId": "Practitioner/123", "patientId": "123"},
        uuid="1234-5678",
        prefetch={},
    )


def test_valid_data_request_construction(cds, valid_data):
    with patch.object(CDSRequest, "__init__", return_value=None) as mock_init:
        cds.construct_request(valid_data, Workflow.patient_view)
        mock_init.assert_called_once_with(
            hook=Workflow.patient_view.value,
            hookInstance="1234-5678",
            context=PatientViewContext(userId="Practitioner/123", patientId="123"),
        )


# def test_invalid_data_raises_error(cds, invalid_data):
#     with pytest.raises(ValueError):
#         cds.construct_request(invalid_data, Workflow.patient_view)


def test_context_mapping(cds, valid_data):
    with patch.dict(
        cds.context_mapping,
        {
            Workflow.patient_view: MagicMock(
                spec=PatientViewContext,
                return_value=PatientViewContext(
                    userId="Practitioner/123", patientId="123"
                ),
            )
        },
    ):
        cds.construct_request(data=valid_data, workflow=Workflow.patient_view)
        cds.context_mapping[Workflow.patient_view].assert_called_once_with(
            **valid_data.context
        )


def test_workflow_validation_decorator(cds, valid_data):
    with pytest.raises(ValueError) as excinfo:
        cds.construct_request(Workflow.notereader_sign_inpatient, valid_data)
    assert "Invalid workflow" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        cds.construct_request(
            data=valid_data, workflow=Workflow.notereader_sign_inpatient
        )
    assert "Invalid workflow" in str(excinfo.value)

    assert cds.construct_request(valid_data, Workflow.patient_view)
