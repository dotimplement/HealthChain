from pathlib import Path
import pytest
import copy
import yaml
import tempfile


from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.models.responses.cdsresponse import CDSResponse, Card
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


@pytest.fixture
def cda_adapter():
    """Provides a reusable instance of the CdaAdapter.

    Use this fixture in tests that require parsing or formatting of CDA documents.

    Example:
        def test_parsing(cda_adapter):
            request = CdaRequest(document="<xml>...</xml>")
            document = cda_adapter.parse(request)
            assert document is not None

    Returns:
        healthchain.io.adapters.CdaAdapter: An instance of the CDA adapter.
    """
    from healthchain.io import CdaAdapter

    return CdaAdapter()


# ########################################
# ######## FHIR Resource Fixtures ########
# ########################################


@pytest.fixture
def empty_bundle():
    """Provides an empty FHIR Bundle resource.

    Use this fixture for tests that need to build a Bundle from scratch by adding
    resources dynamically.

    See Also:
        `test_bundle`: A pre-populated bundle with mixed resources.

    Returns:
        fhir.resources.bundle.Bundle: An empty FHIR Bundle of type 'collection'.
    """
    return create_bundle()


@pytest.fixture
def test_condition():
    """Provides a minimal, generic FHIR Condition resource.

    This fixture is useful for testing components that process a single Condition
    resource without needing specific clinical details.

    Returns:
        fhir.resources.condition.Condition: A minimal FHIR Condition resource with a
        subject, code, and display text.

    See Also:
        `test_condition_list`: For testing with multiple conditions.
    """
    return create_condition(subject="Patient/123", code="123", display="Test Condition")


@pytest.fixture
def test_condition_list():
    """Provides a list containing two FHIR Condition resources.

    Use this fixture for testing components that need to handle lists or collections
    of Condition resources.

    Returns:
        list[fhir.resources.condition.Condition]: A list of two distinct Condition resources.
    """
    return [
        create_condition(subject="Patient/123", code="123", display="Test Condition"),
        create_condition(subject="Patient/123", code="456", display="Test Condition 2"),
    ]


@pytest.fixture
def test_medication():
    """Provides a minimal, generic FHIR MedicationStatement resource.

    This fixture is useful for testing components that process a single
    MedicationStatement without needing specific dosage or timing details.

    Returns:
        fhir.resources.medicationstatement.MedicationStatement: A minimal FHIR
        MedicationStatement resource with a subject, code, and display text.

    See Also:
        `test_medication_with_dosage`: For a more detailed medication resource.
    """
    return create_medication_statement(
        subject="Patient/123", code="456", display="Test Medication"
    )


@pytest.fixture
def test_allergy():
    """Provides a minimal, generic FHIR AllergyIntolerance resource.

    This fixture is useful for testing components that process a single
    AllergyIntolerance resource without needing reaction details.

    Returns:
        fhir.resources.allergyintolerance.AllergyIntolerance: A minimal FHIR
        AllergyIntolerance resource with a patient reference, code, and display text.

    See Also:
        `test_allergy_with_reaction`: For an allergy with reaction details.
    """
    return create_allergy_intolerance(
        patient="Patient/123", code="789", display="Test Allergy"
    )


@pytest.fixture
def test_allergy_with_reaction(test_allergy):
    """Provides an AllergyIntolerance resource with type and reaction details.

    Extends the `test_allergy` fixture by adding `type` and `reaction` fields,
    including manifestation and severity. Use this for testing logic that
    processes detailed allergy information.

    Returns:
        fhir.resources.allergyintolerance.AllergyIntolerance: A detailed FHIR AllergyIntolerance resource.
    """
    test_allergy = copy.deepcopy(test_allergy)
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
    """Provides a MedicationStatement with dosage and effective period.

    Extends the `test_medication` fixture by adding `dosage` (including route and
    timing) and `effectivePeriod`. Use this for testing logic that processes
    medication administration details.

    Returns:
        fhir.resources.medicationstatement.MedicationStatement: A detailed FHIR MedicationStatement resource.
    """
    test_medication = copy.deepcopy(test_medication)
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
    """Provides a DocumentReference with a single, plain-text attachment.

    The attachment data "Test document content" is base64 encoded. Use this
    fixture to test functions that read or process content from a
    DocumentReference.

    Returns:
        fhir.resources.documentreference.DocumentReference: A FHIR DocumentReference with one content attachment.
    """
    return create_document_reference(
        data="Test document content",
        content_type="text/plain",
        description="Test Description",
    )


@pytest.fixture
def doc_ref_with_multiple_content():
    """Provides a DocumentReference with two separate plain-text attachments.

    Contains two attachments with "First content" and "Second content". Use this
    to test logic that handles multiple `content` entries in a single
    DocumentReference.

    Returns:
        fhir.resources.documentreference.DocumentReference: A FHIR DocumentReference with two content attachments.
    """
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
    """Provides a DocumentReference with XML content.

    The attachment has a `contentType` of "text/xml" and data of "<CDA XML>".
    Useful for simulating a DocumentReference that points to a CDA document.

    Returns:
        fhir.resources.documentreference.DocumentReference: A DocumentReference with an XML attachment.
    """
    return create_document_reference(
        data="<CDA XML>",
        content_type="text/xml",
    )


@pytest.fixture
def doc_ref_without_content():
    """Provides an invalid DocumentReference with no attachment data.

    The `attachment` is missing the required `data` or `url` field. This is
    intended for testing error handling and validation logic.

    Returns:
        fhir.resources.documentreference.DocumentReference: An incomplete DocumentReference resource.
    """
    from fhir.resources.attachment import Attachment

    return DocumentReference(
        status="current",
        content=[
            DocumentReferenceContent(attachment=Attachment(contentType="text/plain"))
        ],  # Missing required data or url
    )


@pytest.fixture
def test_bundle():
    """Provides a FHIR Bundle containing one Condition and one MedicationStatement.

    Use this fixture for testing components that process bundles with mixed
    resource types.

    Example:
        def test_bundle_processor(test_bundle):
            conditions = get_resources(test_bundle, "Condition")
            assert len(conditions) == 1

    Returns:
        fhir.resources.bundle.Bundle: A FHIR Bundle with two resource entries.
    """
    bundle = create_bundle()
    bundle.entry = [
        {
            "resource": create_condition(
                subject="Patient/123", code="38341003", display="Hypertension"
            )
        },
        {
            "resource": create_medication_statement(
                subject="Patient/123", code="123454", display="Aspirin"
            )
        },
    ]
    return bundle


@pytest.fixture
def test_document():
    """Provides a `Document` container with pre-populated FHIR lists.

    This fixture creates a `healthchain.io.Document` instance and populates its
    `fhir` attribute with a problem list, medication list, and allergy list,
    each containing one resource.

    Example:
        def test_process_document(test_document):
            # test_document.fhir.problem_list is already populated
            assert len(test_document.fhir.problem_list) == 1
            # Run a pipeline or function on the document
            result = process_clinical_data(test_document)
            assert result is not None

    Returns:
        healthchain.io.containers.Document: A pre-populated Document container for pipeline testing.
    """
    doc = Document(data="Test note")
    doc.fhir.bundle = create_bundle()

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
    """Provides an empty `Document` container with simple text data.

    Returns:
        healthchain.io.containers.Document: A Document container with `data` set and no other annotations.
    """
    return Document(data="This is a sample text for testing.")


@pytest.fixture
def valid_prefetch_data():
    """Provides a dict of FHIR resources for CDS Hooks testing.

    Contains a single prefetch key "document" with a DocumentReference resource.
    Use this for testing services that consume CDS Hooks prefetch data.

    Example:
        def test_prefetch_handler(valid_prefetch_data):
            request = CDSRequest(prefetch=valid_prefetch_data)
            # ... test logic

    Returns:
        dict: A dictionary containing FHIR resources for prefetch data.
    """
    return {
        "document": create_document_reference(
            content_type="text/plain", data="Test document content"
        )
    }


# #################################################
# ######## Request and Response Fixtures ########
# #################################################


@pytest.fixture
def test_cds_request():
    """Provides a sample `CDSRequest` object.

    Represents a typical CDS Hooks request for the `patient-view` hook, including
    context and a minimal Patient resource in the prefetch data.

    Returns:
        healthchain.models.requests.cdsrequest.CDSRequest: A Pydantic model representing a CDS Hooks request.
    """
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
    """Provides a `CDSResponse` object with a single informational card.

    Returns:
        healthchain.models.responses.cdsresponse.CDSResponse: A response containing one `Card` in its `cards` list.
    """
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
    """Provides an empty `CDSResponse` object with no cards.

    Returns:
        healthchain.models.responses.cdsresponse.CDSResponse: A response with an empty `cards` list.
    """
    return CDSResponse(cards=[])


@pytest.fixture
def test_cds_response_multiple_cards():
    """Provides a `CDSResponse` object with multiple cards.

    Contains two cards with different indicators ('info' and 'warning').

    Returns:
        healthchain.models.responses.cdsresponse.CDSResponse: A response containing two `Card` objects.
    """
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
    """Provides a `CdaRequest` object with CDA XML content from a file.

    Reads the content from `./tests/data/test_cda.xml`.

    Returns:
        healthchain.models.requests.cdarequest.CdaRequest: A request object containing a CDA XML string.
    """
    cda_path = Path(__file__).parent / "data" / "test_cda.xml"
    with open(cda_path, "r") as file:
        test_cda = file.read()

    return CdaRequest(document=test_cda)


@pytest.fixture
def test_cda_response():
    """Provides a sample `CdaResponse` object with a mock CDA document.

    Returns:
        healthchain.models.responses.cdaresponse.CdaResponse: A response object with a mock XML document string.
    """
    return CdaResponse(
        document="<ClinicalDocument>Mock CDA Response Document</ClinicalDocument>",
        error=None,
    )


@pytest.fixture
def test_cda_response_with_error():
    """Provides a `CdaResponse` object representing an error condition.

    The `document` is empty and the `error` field is populated.

    Returns:
        healthchain.models.responses.cdaresponse.CdaResponse: A response object indicating an error occurred.
    """
    return CdaResponse(
        document="", error="An error occurred while processing the CDA document"
    )


@pytest.fixture
def test_soap_request():
    """Provides a `CdaRequest` with a sample SOAP XML request from a file.

    Reads the content from `./tests/data/test_soap_request.xml`.

    Returns:
        healthchain.models.requests.cdarequest.CdaRequest: A request object containing a SOAP XML string.
    """
    soap_path = Path(__file__).parent / "data" / "test_soap_request.xml"
    with open(soap_path, "r") as file:
        test_soap = file.read()

    return CdaRequest(document=test_soap)


@pytest.fixture
def config_fixtures():
    """Creates a temporary directory with a complete set of config files.

    This fixture simulates the entire `configs` directory structure, including
    defaults, environments, module-specific configs (interop), and mappings.
    It is suitable for testing both `ConfigManager` and `InteropConfigManager`.

    Example:
        def test_config_loading(config_fixtures):
            # config_fixtures is a Path to a temporary directory
            manager = ConfigManager(config_dir=config_fixtures)
            manager.load()
            assert manager.get_config_value("debug") is True

    Yields:
        pathlib.Path: The path to the temporary configuration directory.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)

        # Create defaults.yaml
        defaults_file = config_dir / "defaults.yaml"
        defaults_content = {
            # Based on the actual defaults.yaml structure
            "defaults": {
                "common": {
                    "id_prefix": "hc-",
                    "timestamp": "%Y%m%d",
                    "reference_name": "#{uuid}name",
                    "subject": {"reference": "Patient/example"},
                },
                "resources": {
                    "Condition": {
                        "clinicalStatus": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                    "code": "unknown",
                                    "display": "Unknown",
                                }
                            ]
                        }
                    },
                    "MedicationStatement": {
                        "status": "unknown",
                        "effectiveDateTime": "{{ now | date: '%Y-%m-%d' }}",
                    },
                },
            },
            # Add interop-specific configs for InteropConfigManager tests
            "interop": {"base_url": "https://api.example.com", "timeout": 30},
        }

        # Create environments directory and files
        env_dir = config_dir / "environments"
        env_dir.mkdir()

        dev_file = env_dir / "development.yaml"
        dev_content = {
            "database": {"name": "healthchain_dev"},
            "debug": True,
            "interop": {"base_url": "https://dev-api.example.com"},
        }

        test_file = env_dir / "testing.yaml"
        test_content = {"database": {"name": "healthchain_test"}, "debug": True}

        prod_file = env_dir / "production.yaml"
        prod_content = {
            "database": {"host": "db.example.com", "name": "healthchain_prod"},
            "debug": False,
        }

        # Create module directory with config files
        interop_dir = config_dir / "interop"
        interop_dir.mkdir()

        # Create cda directory
        cda_dir = interop_dir / "cda"
        cda_dir.mkdir()

        # Create sections directory and files
        sections_dir = cda_dir / "sections"
        sections_dir.mkdir(parents=True)

        # Problems section - needs to comply with ProblemSectionTemplateConfig
        problems_file = sections_dir / "problems.yaml"
        problems_content = {
            "resource": "Condition",
            "resource_template": "cda_fhir/condition",
            "entry_template": "cda_fhir/problem_entry",
            "identifiers": {
                "template_id": "2.16.840.1.113883.10.20.1.11",
                "code": "11450-4",
                "code_system": "2.16.840.1.113883.6.1",
                "code_system_name": "LOINC",
                "display": "Problem List",
            },
            "template": {
                "act": {
                    "template_id": ["2.16.840.1.113883.10.20.1.27"],
                    "status_code": "completed",
                },
                "problem_obs": {
                    "type_code": "SUBJ",
                    "inversion_ind": False,
                    "template_id": ["1.3.6.1.4.1.19376.1.5.3.1.4.5"],
                    "code": "55607006",
                    "code_system": "2.16.840.1.113883.6.96",
                    "status_code": "completed",
                },
                "clinical_status_obs": {
                    "template_id": "2.16.840.1.113883.10.20.1.50",
                    "code": "33999-4",
                    "code_system": "2.16.840.1.113883.6.1",
                    "status_code": "completed",
                },
            },
        }

        # Medications section - needs to comply with MedicationSectionTemplateConfig
        medications_file = sections_dir / "medications.yaml"
        medications_content = {
            "resource": "MedicationStatement",
            "resource_template": "cda_fhir/medication",
            "entry_template": "cda_fhir/medication_entry",
            "identifiers": {
                "template_id": "2.16.840.1.113883.10.20.1.8",
                "code": "10160-0",
                "code_system": "2.16.840.1.113883.6.1",
                "code_system_name": "LOINC",
                "display": "Medications",
            },
            "template": {
                "substance_admin": {
                    "template_id": ["2.16.840.1.113883.10.20.1.24"],
                    "status_code": "completed",
                    "class_code": "SBADM",
                    "mood_code": "EVN",
                },
                "manufactured_product": {
                    "template_id": ["2.16.840.1.113883.10.20.1.53"],
                    "code": "200000",
                    "code_system": "2.16.840.1.113883.6.88",
                },
                "clinical_status_obs": {
                    "template_id": "2.16.840.1.113883.10.20.1.47",
                    "code": "33999-4",
                    "code_system": "2.16.840.1.113883.6.1",
                    "status_code": "completed",
                },
            },
        }

        # Allergies section - needs to comply with AllergySectionTemplateConfig
        allergies_file = sections_dir / "allergies.yaml"
        allergies_content = {
            "resource": "AllergyIntolerance",
            "resource_template": "cda_fhir/allergy",
            "entry_template": "cda_fhir/allergy_entry",
            "identifiers": {
                "template_id": "2.16.840.1.113883.10.20.1.2",
                "code": "48765-2",
                "code_system": "2.16.840.1.113883.6.1",
                "code_system_name": "LOINC",
                "display": "Allergies",
            },
            "template": {
                "act": {
                    "template_id": ["2.16.840.1.113883.10.20.1.27"],
                    "status_code": "completed",
                },
                "allergy_obs": {
                    "template_id": ["2.16.840.1.113883.10.20.1.18"],
                    "code": "416098002",
                    "code_system": "2.16.840.1.113883.6.96",
                    "status_code": "completed",
                },
                "reaction_obs": {
                    "template_id": ["2.16.840.1.113883.10.20.1.54"],
                    "code": "59037007",
                    "code_system": "2.16.840.1.113883.6.96",
                },
                "severity_obs": {
                    "template_id": ["2.16.840.1.113883.10.20.1.55"],
                    "code": "39579001",
                    "code_system": "2.16.840.1.113883.6.96",
                },
                "clinical_status_obs": {
                    "template_id": "2.16.840.1.113883.10.20.1.39",
                    "code": "33999-4",
                    "code_system": "2.16.840.1.113883.6.1",
                    "status_code": "completed",
                },
            },
        }

        # Create document directory and file
        document_dir = cda_dir / "document"
        document_dir.mkdir()

        # Document config - needs to comply with DocumentConfig
        ccd_file = document_dir / "ccd.yaml"
        ccd_content = {
            "type_id": {"root": "2.16.840.1.113883.1.3", "extension": "POCD_HD000040"},
            "code": {
                "code": "34133-9",
                "code_system": "2.16.840.1.113883.6.1",
                "code_system_name": "LOINC",
                "display": "Summarization of Episode Note",
            },
            "confidentiality_code": {
                "code": "N",
                "code_system": "2.16.840.1.113883.5.25",
            },
            "language_code": "en-US",
            "templates": {"section": "cda_section", "document": "cda_document"},
            "structure": {
                "header": {"include_patient": True, "include_author": True},
                "body": {"structured_body": True},
            },
        }

        # Create mappings directory
        mappings_dir = config_dir / "mappings"
        mappings_dir.mkdir()

        mapping_file = mappings_dir / "snomed_loinc.yaml"
        mapping_content = {
            "snomed_to_loinc": {"55607006": "11450-4", "73211009": "10160-0"}
        }

        # Create templates directory
        templates_dir = config_dir / "templates"
        templates_dir.mkdir()

        # Write all the files
        with open(defaults_file, "w") as f:
            yaml.dump(defaults_content, f)

        with open(dev_file, "w") as f:
            yaml.dump(dev_content, f)

        with open(test_file, "w") as f:
            yaml.dump(test_content, f)

        with open(prod_file, "w") as f:
            yaml.dump(prod_content, f)

        with open(problems_file, "w") as f:
            yaml.dump(problems_content, f)

        with open(medications_file, "w") as f:
            yaml.dump(medications_content, f)

        with open(allergies_file, "w") as f:
            yaml.dump(allergies_content, f)

        with open(ccd_file, "w") as f:
            yaml.dump(ccd_content, f)

        with open(mapping_file, "w") as f:
            yaml.dump(mapping_content, f)

        yield config_dir


@pytest.fixture
def real_config_dir():
    """Provides the path to the actual `configs` directory in the project.

    This fixture allows tests to run against the real, checked-in configuration
    files. It will skip tests if the directory is not found.

    Returns:
        pathlib.Path: The path to the project's `configs` directory.
    """
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "configs"

    if not config_dir.exists():
        pytest.skip("Actual config directory not found. Skipping ConfigManager tests.")

    return config_dir
