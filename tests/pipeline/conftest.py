import pytest
from unittest.mock import patch
from healthchain.io.cdaconnector import CdaConnector
from healthchain.io.cdsfhirconnector import CdsFhirConnector
from healthchain.io.containers import Document
from healthchain.io.containers.document import (
    CdsAnnotations,
    HL7Data,
)
from healthchain.models.data.ccddata import CcdData
from healthchain.models.data.concept import (
    AllergyConcept,
    ConceptLists,
    MedicationConcept,
    ProblemConcept,
)
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.pipeline.base import BasePipeline
from healthchain.models.responses.cdsresponse import CDSResponse, Card
from healthchain.models.data.cdsfhirdata import CdsFhirData


@pytest.fixture
def cda_connector():
    return CdaConnector()


@pytest.fixture
def cds_fhir_connector():
    return CdsFhirConnector(hook_name="patient-view")


@pytest.fixture
def mock_cda_connector():
    with patch("healthchain.io.cdaconnector.CdaConnector") as mock:
        connector_instance = mock.return_value

        # Mock the input method
        connector_instance.input.return_value = Document(
            data="Original note",
            _hl7=HL7Data(
                _ccd_data=CcdData(
                    concepts=ConceptLists(
                        problems=[
                            ProblemConcept(
                                code="38341003",
                                code_system="2.16.840.1.113883.6.96",
                                code_system_name="SNOMED CT",
                                display_name="Hypertension",
                            )
                        ],
                        medications=[
                            MedicationConcept(
                                code="123454",
                                code_system="2.16.840.1.113883.6.96",
                                code_system_name="SNOMED CT",
                                display_name="Aspirin",
                            )
                        ],
                        allergies=[
                            AllergyConcept(
                                code="70618",
                                code_system="2.16.840.1.113883.6.96",
                                code_system_name="SNOMED CT",
                                display_name="Allergy to peanuts",
                            )
                        ],
                    ),
                ),
            ),
        )

        # Mock the output method
        connector_instance.output.return_value = CdaResponse(
            document="<xml>Updated CDA</xml>"
        )

        yield mock


@pytest.fixture
def mock_cda_annotator():
    with patch("healthchain.io.cdaconnector.CdaAnnotator") as mock:
        mock_instance = mock.return_value
        mock_instance.from_xml.return_value = mock_instance
        mock_instance.problem_list = [
            ProblemConcept(
                code="38341003",
                code_system="2.16.840.1.113883.6.96",
                code_system_name="SNOMED CT",
                display_name="Hypertension",
            )
        ]
        mock_instance.medication_list = [
            MedicationConcept(
                code="123454",
                code_system="2.16.840.1.113883.6.96",
                code_system_name="SNOMED CT",
                display_name="Aspirin",
            )
        ]
        mock_instance.allergy_list = [
            AllergyConcept(
                code="70618",
                code_system="2.16.840.1.113883.6.96",
                code_system_name="SNOMED CT",
                display_name="Allergy to peanuts",
            )
        ]
        mock_instance.note = "Sample Note"
        yield mock


@pytest.fixture
def mock_basic_pipeline():
    class TestPipeline(BasePipeline):
        def configure_pipeline(self, model_path: str) -> None:
            pass

    return TestPipeline()


@pytest.fixture
def mock_model():
    with patch("healthchain.pipeline.modelrouter.ModelRouter.get_integration") as mock:
        model_instance = mock.return_value
        model_instance.return_value = Document(
            data="Processed note",
            _concepts=ConceptLists(
                problems=[
                    ProblemConcept(
                        code="38341003",
                        code_system="2.16.840.1.113883.6.96",
                        code_system_name="SNOMED CT",
                        display_name="Hypertension",
                    )
                ],
                medications=[
                    MedicationConcept(
                        code="123454",
                        code_system="2.16.840.1.113883.6.96",
                        code_system_name="SNOMED CT",
                        display_name="Aspirin",
                    )
                ],
                allergies=[
                    AllergyConcept(
                        code="70618",
                        code_system="2.16.840.1.113883.6.96",
                        code_system_name="SNOMED CT",
                        display_name="Allergy to peanuts",
                    )
                ],
            ),
        )
        yield mock


@pytest.fixture
def mock_llm():
    with patch("healthchain.pipeline.components.llm.LLM") as mock:
        llm_instance = mock.return_value
        llm_instance.return_value = Document(
            data="Summarized discharge information",
            _cds=CdsAnnotations(
                _cards=[
                    Card(
                        summary="Summarized discharge information",
                        detail="Patient John Doe was discharged. Encounter details...",
                        indicator="info",
                        source={"label": "Summarization LLM"},
                    )
                ],
            ),
        )
        yield mock


@pytest.fixture
def mock_cds_fhir_connector():
    with patch("healthchain.io.cdsfhirconnector.CdsFhirConnector") as mock:
        connector_instance = mock.return_value

        # Mock the input method
        connector_instance.input.return_value = Document(
            data="Original FHIR data",
            _hl7=HL7Data(
                _fhir_data=CdsFhirData(
                    context={"patientId": "123", "encounterId": "456"},
                    prefetch={
                        "resourceType": "Bundle",
                        "entry": [
                            {
                                "resource": {
                                    "resourceType": "Patient",
                                    "id": "123",
                                    "name": [{"family": "Doe", "given": ["John"]}],
                                    "gender": "male",
                                    "birthDate": "1970-01-01",
                                }
                            },
                        ],
                    },
                ),
            ),
        )

        # Mock the output method
        connector_instance.output.return_value = CDSResponse(
            cards=[
                Card(
                    summary="Summarized discharge information",
                    detail="Patient John Doe was discharged. Encounter details...",
                    indicator="info",
                    source={"label": "Summarization LLM"},
                )
            ]
        )

        yield mock
