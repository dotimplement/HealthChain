import pytest

from unittest.mock import Mock

from healthchain.base import BaseStrategy, BaseUseCase
from healthchain.cda_parser.cdaannotator import CdaAnnotator
from healthchain.models.hooks.prefetch import Prefetch
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.requests.cdsrequest import CDSRequest
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
from healthchain.io.containers import Document
from healthchain.fhir import (
    create_bundle,
    create_condition,
    create_medication_statement,
    create_allergy_intolerance,
    create_single_attachment,
    create_document_reference,
    create_single_codeable_concept,
    create_single_reaction,
)

from fhir.resources.documentreference import DocumentReference, DocumentReferenceContent


# TODO: Tidy up fixtures


# FHIR resource fixtures


@pytest.fixture
def empty_bundle():
    """Create an empty bundle for testing."""
    return create_bundle()


@pytest.fixture
def test_condition():
    """Create a test condition."""
    return create_condition(subject="Patient/123", code="123", display="Test Condition")


@pytest.fixture
def test_medication():
    """Create a test medication statement."""
    return create_medication_statement(
        subject="Patient/123", code="456", display="Test Medication"
    )


@pytest.fixture
def test_allergy():
    """Create a test allergy intolerance."""
    return create_allergy_intolerance(
        patient="Patient/123", code="789", display="Test Allergy"
    )


@pytest.fixture
def test_allergy_with_reaction(test_allergy):
    test_allergy.type = create_single_codeable_concept(
        code="ABC", display="Test Allergy", system="http://snomed.info/sct"
    )

    test_allergy.reaction = create_single_reaction(
        code="DEF",
        display="Test Allergy",
        system="http://snomed.info/sct",
        severity="GHI",
    )
    return test_allergy


@pytest.fixture
def test_medication_with_dosage(test_medication):
    test_medication.dosage = [
        {
            "doseAndRate": [{"doseQuantity": {"value": 500, "unit": "mg"}}],
            "route": create_single_codeable_concept(
                code="test", display="test", system="http://snomed.info/sct"
            ),
            "timing": {"repeat": {"period": 1, "periodUnit": "d"}},
        }
    ]

    # Add effective period
    test_medication.effectivePeriod = {"end": "2022-10-20"}
    return test_medication


@pytest.fixture
def doc_ref_with_content():
    """Create a DocumentReference with single text content."""
    return create_document_reference(
        data="Test document content",
        content_type="text/plain",
        description="Test Description",
    )


@pytest.fixture
def doc_ref_with_multiple_content():
    """Create a DocumentReference with multiple text content."""
    doc_ref = create_document_reference(
        data="First content",
        content_type="text/plain",
        description="Test Description",
    )
    doc_ref.content.append(
        DocumentReferenceContent(
            attachment=create_single_attachment(
                data="Second content", content_type="text/plain"
            )
        )
    )
    return doc_ref


@pytest.fixture
def doc_ref_with_cda_xml():
    """Create a DocumentReference with CDA XML content."""
    return create_document_reference(
        data="<CDA XML>",
        content_type="text/xml",
    )


@pytest.fixture
def doc_ref_without_content():
    """Create a DocumentReference without content for error testing."""
    return DocumentReference(
        status="current",
        content=[
            {"attachment": {"contentType": "text/plain"}}
        ],  # Missing required data
    )


@pytest.fixture
def test_document():
    """Create a test document with FHIR resources."""
    doc = Document(data="Test note")
    doc.fhir.set_bundle(create_bundle())

    # Add test FHIR resources
    problem_list = create_condition(
        subject="Patient/123", code="38341003", display="Hypertension"
    )
    doc.fhir.problem_list = [problem_list]

    medication_list = create_medication_statement(
        subject="Patient/123", code="123454", display="Aspirin"
    )
    doc.fhir.medication_list = [medication_list]

    allergy_list = create_allergy_intolerance(
        patient="Patient/123", code="70618", display="Allergy to peanuts"
    )
    doc.fhir.allergy_list = [allergy_list]

    return doc


@pytest.fixture
def test_empty_document():
    return Document(data="This is a sample text for testing.")


class MockDataGenerator:
    def __init__(self) -> None:
        self.generated_data = {"document": create_bundle()}
        self.workflow = None

    def set_workflow(self, workflow):
        self.workflow = workflow


@pytest.fixture
def cdsservices():
    return CDSServices()


@pytest.fixture
def cds_strategy():
    return ClinicalDecisionSupportStrategy()


@pytest.fixture
def valid_prefetch_data():
    return Prefetch(
        prefetch={
            "document": create_document_reference(
                content_type="text/plain", data="Test document content"
            )
        }
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


# Sandbox fixtures


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


# Test request and response fixtures


@pytest.fixture
def test_cds_request():
    cds_dict = {
        "hook": "patient-view",
        "hookInstance": "29e93987-c345-4cb7-9a92-b5136289c2a4",
        "context": {"userId": "Practitioner/123", "patientId": "123"},
        "prefetch": {
            "patient": {
                "resourceType": "Patient",
                "id": "123",
                "name": [{"family": "Doe", "given": ["John"]}],
                "gender": "male",
                "birthDate": "1970-01-01",
            },
        },
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
def cda_annotator_with_data():
    with open("./tests/data/test_cda.xml", "r") as file:
        test_cda = file.read()

    return CdaAnnotator.from_xml(test_cda)


@pytest.fixture
def cda_annotator_without_template_id():
    with open("./tests/data/test_cda_without_template_id.xml", "r") as file:
        test_cda_without_template_id = file.read()
    return CdaAnnotator.from_xml(test_cda_without_template_id)
