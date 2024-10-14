import dataclasses
import logging
import pytest

from unittest.mock import Mock
from pydantic import BaseModel

from healthchain.base import BaseStrategy, BaseUseCase
from healthchain.cda_parser.cdaannotator import CdaAnnotator
from healthchain.fhir_resources.bundleresources import Bundle, BundleEntry
from healthchain.models import CDSRequest, CdsFhirData
from healthchain.models.data.ccddata import CcdData
from healthchain.models.data.concept import (
    AllergyConcept,
    MedicationConcept,
    ProblemConcept,
)
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.models.responses.cdsresponse import CDSResponse, Card
from healthchain.service.soap.epiccdsservice import CDSServices
from healthchain.use_cases.cds import (
    ClinicalDecisionSupport,
    ClinicalDecisionSupportStrategy,
)
from healthchain.clients.ehrclient import EHRClient
from healthchain.decorators import sandbox
from healthchain.use_cases.clindoc import ClinicalDocumentation
from healthchain.workflows import UseCaseType

# TODO: Tidy up fixtures


@pytest.fixture(autouse=True)
def setup_caplog(caplog):
    caplog.set_level(logging.WARNING)
    return caplog


class MockBundle(BaseModel):
    condition: str = "test"


# TEMP
@dataclasses.dataclass
class synth_data:
    context: dict
    prefetch: MockBundle


class MockDataGenerator:
    def __init__(self) -> None:
        self.data = CdsFhirData(context={}, prefetch=Bundle(entry=[BundleEntry()]))
        # self.data = synth_data(context={}, prefetch=MockBundle())
        self.workflow = None

    def set_workflow(self, workflow):
        self.workflow = workflow


@pytest.fixture
def cds_strategy():
    return ClinicalDecisionSupportStrategy()


@pytest.fixture
def valid_data():
    return CdsFhirData(
        context={"userId": "Practitioner/123", "patientId": "123"},
        prefetch=Bundle(entry=[BundleEntry()]),
    )


@pytest.fixture
def invalid_data():
    return CdsFhirData(
        context={"invalidId": "Practitioner", "patientId": "123"},
        prefetch=Bundle(entry=[BundleEntry()]),
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


@pytest.fixture
def test_cds_response_single_card():
    return CDSResponse(
        cards=[
            Card(
                summary="Test Card",
                indicator="info",
                source={"label": "Test Source"},
                detail="This is a test card for CDS response",
            )
        ]
    )


@pytest.fixture
def test_cds_response_empty():
    return CDSResponse(cards=[])


@pytest.fixture
def test_cds_response_multiple_cards():
    return CDSResponse(
        cards=[
            Card(
                summary="Test Card 1", indicator="info", source={"label": "Test Source"}
            ),
            Card(
                summary="Test Card 2",
                indicator="warning",
                source={"label": "Test Source"},
            ),
        ]
    )


@pytest.fixture
def mock_client_decorator():
    def mock_client_decorator(func):
        func.is_client = True
        return func

    return mock_client_decorator


@pytest.fixture
def mock_api_decorator():
    def mock_api_decorator(func):
        func.is_service_route = True
        return func

    return mock_api_decorator


@pytest.fixture
def correct_sandbox_class(mock_api_decorator, mock_client_decorator):
    @sandbox
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @mock_client_decorator
        def foo(self):
            return "foo"

        @mock_api_decorator
        def bar(self):
            return "bar"

    return testSandbox


@pytest.fixture
def incorrect_client_num_sandbox_class(mock_api_decorator, mock_client_decorator):
    @sandbox
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @mock_client_decorator
        def foo(self):
            return "foo"

        @mock_client_decorator
        def foo2(self):
            return "foo"

        @mock_api_decorator
        def bar(self):
            return "bar"

    return testSandbox


@pytest.fixture
def incorrect_api_num_sandbox_class(mock_api_decorator, mock_client_decorator):
    @sandbox
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @mock_client_decorator
        def foo(self):
            return "foo"

        @mock_api_decorator
        def bar(self):
            return "bar"

        @mock_api_decorator
        def bar2(self):
            return "bar"

    return testSandbox


@pytest.fixture
def correct_sandbox_class_with_args(mock_api_decorator, mock_client_decorator):
    @sandbox(service_config={"host": "123.0.0.1", "port": 9000, "ssl_keyfile": "foo"})
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @mock_client_decorator
        def foo(self):
            return "foo"

        @mock_api_decorator
        def bar(self):
            return "bar"

    return testSandbox


@pytest.fixture
def correct_sandbox_class_with_incorrect_args(
    mock_api_decorator, mock_client_decorator
):
    @sandbox(incorrect_arg={"something": 8000})
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

        @mock_client_decorator
        def foo(self):
            return "foo"

        @mock_api_decorator
        def bar(self):
            return "bar"

    return testSandbox


@pytest.fixture
def missing_funcs_sandbox_class():
    @sandbox
    class testSandbox(ClinicalDecisionSupport):
        def __init__(self) -> None:
            pass

    return testSandbox


@pytest.fixture
def wrong_subclass_sandbox_class():
    @sandbox
    class testSandbox:
        def __init__(self) -> None:
            pass

    return testSandbox


@pytest.fixture
def cds():
    service_api_mock = Mock()
    service_config = {"host": "localhost", "port": 8080}
    service_mock = Mock()
    client_mock = Mock()
    client_mock.workflow.value = "hook1"
    return ClinicalDecisionSupport(
        service_api=service_api_mock,
        service_config=service_config,
        service=service_mock,
        client=client_mock,
    )


@pytest.fixture
def clindoc():
    service_api_mock = Mock()
    service_config = {"host": "localhost", "port": 8080}
    service_mock = Mock()
    client_mock = Mock()
    client_mock.workflow.value = "hook1"
    return ClinicalDocumentation(
        service_api=service_api_mock,
        service_config=service_config,
        service=service_mock,
        client=client_mock,
    )


@pytest.fixture
def test_cda_request():
    with open("./tests/data/test_cda.xml", "r") as file:
        test_cda = file.read()

    return CdaRequest(document=test_cda)


@pytest.fixture
def test_cda_response():
    return CdaResponse(
        document="<ClinicalDocument>Mock CDA Response Document</ClinicalDocument>",
        error=None,
    )


@pytest.fixture
def test_cda_response_with_error():
    return CdaResponse(
        document="", error="An error occurred while processing the CDA document"
    )


@pytest.fixture
def test_soap_request():
    with open("./tests/data/test_soap_request.xml", "r") as file:
        test_soap = file.read()

    return CdaRequest(document=test_soap)


@pytest.fixture
def test_ccd_data():
    return CcdData(
        problems=[ProblemConcept(code="test")],
        medications=[MedicationConcept(code="test")],
        allergies=[AllergyConcept(code="test")],
    )


@pytest.fixture
def test_multiple_ccd_data():
    return CcdData(
        problems=[ProblemConcept(code="test1"), ProblemConcept(code="test2")],
        medications=[MedicationConcept(code="test1"), MedicationConcept(code="test2")],
        allergies=[AllergyConcept(code="test1"), AllergyConcept(code="tes2")],
    )


@pytest.fixture
def cda_annotator():
    with open("./tests/data/test_cda.xml", "r") as file:
        test_cda = file.read()

    return CdaAnnotator.from_xml(test_cda)


@pytest.fixture
def cdsservices():
    return CDSServices()
