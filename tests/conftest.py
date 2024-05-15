import dataclasses
import pytest

from unittest.mock import Mock

from healthchain.base import BaseStrategy, BaseUseCase, UseCaseType
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.use_cases.cds import ClinicalDecisionSupportStrategy
from healthchain.clients import EHRClient


# TEMP
@dataclasses.dataclass
class synth_data:
    context: dict
    uuid: str
    prefetch: dict


@pytest.fixture
def cds_strategy():
    return ClinicalDecisionSupportStrategy()


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
        context={"invalidId": "Practitioner", "patientId": "123"},
        uuid="1234-5678",
        prefetch={},
    )


@pytest.fixture
def mock_function():
    return Mock()


@pytest.fixture
def mock_workflow():
    return Mock()


@pytest.fixture
def mock_strategy():
    mock = Mock()
    mock.construct_request = Mock(
        return_value=Mock(model_dump_json=Mock(return_value="{}"))
    )
    return mock


@pytest.fixture
def ehr_client(mock_function, mock_workflow, mock_strategy):
    return EHRClient(mock_function, mock_workflow, mock_strategy)


@pytest.fixture(scope="function")
def mock_cds_strategy() -> BaseStrategy:
    class MockClinicalDecisionSupportStrategy(BaseStrategy):
        def _validate_data(self):
            pass

        construct_request = Mock(
            return_value=Mock(model_dump_json=Mock(return_value="{}"))
        )

    return MockClinicalDecisionSupportStrategy()


@pytest.fixture
def mock_cds() -> BaseUseCase:
    class MockClinicalDecisionSupportStrategy(BaseStrategy):
        def _validate_data(self):
            pass

        construct_request = Mock(
            return_value=Mock(model_dump_json=Mock(return_value="{}"))
        )

    class MockClinicalDecisionSupport(BaseUseCase):
        type = UseCaseType.cds
        endpoints = {}
        strategy = MockClinicalDecisionSupportStrategy()

    return MockClinicalDecisionSupport


@pytest.fixture
def test_cds_request():
    cds_dict = {
        "hook": "patient-view",
        "hookInstance": "29e93987-c345-4cb7-9a92-b5136289c2a4",
        "context": {"userId": "Practitioner/123", "patientId": "123"},
    }
    return CDSRequest(**cds_dict)
