"""
🏥 HealthChain Complete Sandbox Demo

A comprehensive demonstration of HealthChain's capabilities including:
- Medical coding and summarization pipelines
- CDS Hooks and NoteReader services
- FHIR Gateway with custom handlers
- Event-driven processing
- Sandbox environments for testing

This script showcases the full HealthChain ecosystem in action.

Prerequisites:
- HUGGINGFACEHUB_API_TOKEN environment variable (will prompt if not set)
- ./resources/uclh_cda.xml
- ./cookbook/data/discharge_notes.csv
"""

import getpass
import os
import threading
import uvicorn
import requests
import json
import glob
from datetime import datetime
from time import sleep
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from spacy.tokens import Span

# HealthChain imports
from healthchain.gateway import (
    HealthChainAPI,
    NoteReaderService,
    EHREvent,
    EHREventType,
)
from healthchain.gateway.cds import CDSHooksService
from healthchain.gateway.fhir import FHIRGateway
from healthchain.gateway.events.dispatcher import local_handler
from healthchain.io import Document
from healthchain.models.requests import CdaRequest
from healthchain.models.requests.cdsrequest import CDSRequest
from healthchain.models.responses import CdaResponse
from healthchain.models.responses.cdsresponse import CDSResponse
from healthchain.pipeline.medicalcodingpipeline import MedicalCodingPipeline
from healthchain.pipeline.summarizationpipeline import SummarizationPipeline

# FHIR imports
from fhir.resources.documentreference import DocumentReference
from fhir.resources.patient import Patient
from fhir.resources.meta import Meta
from healthchain.sandbox import SandboxClient
from healthchain.fhir import create_document_reference

from dotenv import load_dotenv

load_dotenv()


# Configuration
CONFIG = {
    "server": {
        "host": "localhost",
        "port": 8000,
        "startup_delay": 5,
    },
    "data": {
        "cda_document_path": "./resources/uclh_cda.xml",
        "discharge_notes_path": "./cookbook/data/discharge_notes.csv",
    },
    "models": {
        "spacy_model": "en_core_sci_sm",
        "summarization_model": "google/pegasus-xsum",
    },
    "workflows": {
        "notereader": "sign-note-inpatient",
        "cds": "encounter-discharge",
    },
}


def print_section(title: str, emoji: str = "🔧"):
    """Print a nicely formatted section header"""
    print(f"\n{'='*60}")
    print(f"{emoji} {title}")
    print("=" * 60)


def print_step(message: str):
    """Print a step message"""
    print(f"🔹 {message}")


def print_success(message: str):
    """Print success message"""
    print(f"✅ {message}")


def print_warning(message: str):
    """Print warning message"""
    print(f"⚠️ {message}")


def print_error(message: str):
    """Print error message"""
    print(f"❌ {message}")


def print_info(message: str):
    """Print info message"""
    print(f"ℹ️ {message}")


# Validation result structures
class ValidationLevel(Enum):
    """Validation result levels"""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check"""

    passed: bool
    message: str
    details: dict = field(default_factory=dict)
    level: ValidationLevel = ValidationLevel.INFO

    def print(self):
        """Print validation result with appropriate formatting"""
        if self.level == ValidationLevel.SUCCESS:
            print_success(self.message)
        elif self.level == ValidationLevel.WARNING:
            print_warning(self.message)
        elif self.level == ValidationLevel.ERROR:
            print_error(self.message)
        else:
            print_info(self.message)

        # Print details if present
        for key, value in self.details.items():
            if isinstance(value, list):
                print(f"  {key}:")
                for item in value:
                    print(f"    - {item}")
            else:
                print(f"  {key}: {value}")


def make_api_request(
    url: str, method: str = "get", timeout: int = 10, **kwargs
) -> Optional[requests.Response]:
    """
    Make HTTP request with consistent error handling

    Args:
        url: URL to request
        method: HTTP method (get, post, etc.)
        timeout: Request timeout in seconds
        **kwargs: Additional arguments to pass to requests

    Returns:
        Response object or None if request failed
    """
    try:
        response = getattr(requests, method.lower())(url, timeout=timeout, **kwargs)
        return response
    except Exception as e:
        print_error(f"Request failed: {str(e)}")
        return None


def validate_prerequisites():
    """Validate that all required files exist before running"""
    print_section("Validating Prerequisites", "🔍")

    required_files = {
        "CDA Document": CONFIG["data"]["cda_document_path"],
        "Discharge Notes": CONFIG["data"]["discharge_notes_path"],
    }

    missing = []
    for name, path in required_files.items():
        if not os.path.exists(path):
            missing.append(f"{name}: {path}")
        else:
            print_success(f"Found {name}: {path}")

    if missing:
        print_error("Missing required files:")
        for file in missing:
            print(f"  ❌ {file}")
        print("\nPlease ensure these files exist before running the demo.")
        raise SystemExit(1)

    print_success("All prerequisites validated")


def setup_environment():
    """Setup required environment variables"""
    print_section("Environment Setup", "🌍")

    if not os.getenv("HUGGINGFACEHUB_API_TOKEN"):
        print_step("HuggingFace API token required for summarization pipeline")
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = getpass.getpass(
            "Enter your HuggingFace token: "
        )
        print_success("HuggingFace token configured")
    else:
        print_success("HuggingFace token already configured")


def create_pipelines():
    """Create and configure ML pipelines"""
    print_section("Creating ML Pipelines", "🧠")

    # Medical coding pipeline
    print_step("Setting up medical coding pipeline...")
    coding_pipeline = MedicalCodingPipeline.from_model_id(
        CONFIG["models"]["spacy_model"], source="spacy"
    )

    # Add custom entity linking
    @coding_pipeline.add_node(position="after", reference="SpacyNLP")
    def link_entities(doc: Document) -> Document:
        """Add CUI codes to medical entities"""
        if not Span.has_extension("cui"):
            Span.set_extension("cui", default=None)

        spacy_doc = doc.nlp.get_spacy_doc()

        # Simple dummy linker for demo purposes
        dummy_linker = {
            "fever": "C0006477",
            "cough": "C0006477",
            "cold": "C0006477",
            "flu": "C0006477",
            "headache": "C0006477",
            "sore throat": "C0006477",
        }

        for ent in spacy_doc.ents:
            if ent.text in dummy_linker:
                ent._.cui = dummy_linker[ent.text]

        return doc

    print_success("Medical coding pipeline created")

    # Summarization pipeline
    print_step("Setting up summarization pipeline...")
    summarization_pipeline = SummarizationPipeline.from_model_id(
        CONFIG["models"]["summarization_model"],
        source="huggingface",
        task="summarization",
    )
    print_success("Summarization pipeline created")

    return coding_pipeline, summarization_pipeline


def setup_event_handlers():
    """Configure event handlers for the system"""
    print_section("Setting Up Event Handlers", "📡")

    # Event collector for validation
    captured_events = []

    @local_handler.register(event_name=EHREventType.NOTEREADER_PROCESS_NOTE.value)
    async def handle_notereader_event(event):
        """Handler for NoteReader events"""
        event_name, payload = event
        print(f"📋 NoteReader Event: {payload['source_system']}")
        print(f"   Custom ID: {payload['payload'].get('custom_id', 'N/A')}")
        captured_events.append(("notereader", event_name))
        return True

    @local_handler.register(event_name="*")
    async def log_all_events(event):
        """Catch-all handler for system events"""
        event_name, payload = event
        print(f"🔔 System Event: {event_name}")
        captured_events.append(("global", event_name))
        return True

    print_success("Event handlers registered")

    # Store the captured events list for later validation
    setup_event_handlers.captured_events = captured_events


def create_services(coding_pipeline, summarization_pipeline):
    """Create and configure HealthChain services"""
    print_section("Creating HealthChain Services", "⚕️")

    # Create services
    note_service = NoteReaderService()
    cds_service = CDSHooksService()
    fhir_gateway = FHIRGateway()

    # Configure CDS Hooks
    @cds_service.hook("encounter-discharge", id="discharge-summary")
    def handle_discharge_summary(request: CDSRequest) -> CDSResponse:
        """Process discharge summaries with AI"""
        result = summarization_pipeline.process_request(request)
        return result

    print_success("CDS Hooks service configured")

    # Configure NoteReader
    @note_service.method("ProcessDocument")
    def process_document(cda_request: CdaRequest) -> CdaResponse:
        """Process clinical documents with NLP"""
        result = coding_pipeline.process_request(cda_request)
        return result

    print_success("NoteReader service configured")

    # Configure FHIR Gateway handlers
    @fhir_gateway.transform(DocumentReference)
    def enhance_document(id: str, source: str) -> DocumentReference:
        """Transform documents with AI enhancements"""
        print(f"📄 Enhancing document {id} from {source}")

        # Create enhanced document
        document = create_document_reference(
            data="AI-enhanced clinical document",
            content_type="text/xml",
            description="Document enhanced with HealthChain AI processing",
        )

        # Add AI summary extension
        document.extension = [
            {
                "url": "http://healthchain.org/extension/ai-summary",
                "valueString": "This document has been enhanced with AI-powered analysis",
            }
        ]

        # Add processing metadata
        document.meta = Meta(
            lastUpdated=datetime.now().isoformat(),
            tag=[{"system": "http://healthchain.org/tag", "code": "ai-enhanced"}],
        )

        return document

    @fhir_gateway.aggregate(Patient)
    def aggregate_patient_data(id: str, sources: List[str]) -> Patient:
        """Aggregate patient data from multiple sources"""
        print(f"👤 Aggregating patient {id} from sources: {', '.join(sources)}")

        patient = Patient()
        patient.id = id
        patient.gender = "unknown"
        patient.birthDate = "1990-01-01"

        return patient

    print_success("FHIR Gateway handlers configured")

    # Setup custom event creator
    def custom_event_creator(operation, *args):
        """Create customized events for integration tracking"""
        return EHREvent(
            event_type=EHREventType.NOTEREADER_PROCESS_NOTE,
            source_system="HealthChain-Demo",
            timestamp=datetime.now(),
            payload={
                "demo_id": "sandbox-123",
                "operation": operation,
            },
            metadata={
                "environment": "sandbox",
                "priority": "demo",
            },
        )

    note_service.events.set_event_creator(custom_event_creator)
    print_success("Custom event creator configured")

    return note_service, cds_service, fhir_gateway


def create_app(note_service, cds_service, fhir_gateway):
    """Create and configure the main HealthChain application"""
    print_section("Creating HealthChain Application", "🏥")

    app = HealthChainAPI()

    # Register all services
    app.register_service(note_service)
    app.register_service(cds_service)
    app.register_gateway(fhir_gateway)

    print_success("HealthChain application created and services registered")
    return app


def create_sandboxes():
    """Create sandbox environments for testing"""
    print_section("Creating Sandbox Environments", "🏖️")

    base_url = f"http://{CONFIG['server']['host']}:{CONFIG['server']['port']}"

    # NoteReader Sandbox
    notereader_client = SandboxClient(
        url=base_url + "/notereader/?wsdl",
        workflow=CONFIG["workflows"]["notereader"],
        protocol="soap",
    )

    # Load CDA document
    notereader_client.load_from_path(CONFIG["data"]["cda_document_path"])

    # CDS Hooks Sandbox
    cds_client = SandboxClient(
        url=base_url + "/cds/cds-services/discharge-summary",
        workflow=CONFIG["workflows"]["cds"],
        protocol="rest",
    )

    # Load discharge notes
    cds_client.load_free_text(
        csv_path=CONFIG["data"]["discharge_notes_path"],
        column_name="text",
    )

    print_success("Sandbox environments created")
    return notereader_client, cds_client


def start_server(app):
    """Start the HealthChain server in a separate thread"""
    print_section("Starting HealthChain Server", "🚀")

    def run_server():
        uvicorn.run(
            app,
            host=CONFIG["server"]["host"],
            port=CONFIG["server"]["port"],
            log_level="info",
        )

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    print_step(
        f"Server starting on {CONFIG['server']['host']}:{CONFIG['server']['port']}"
    )
    print_step(f"Waiting {CONFIG['server']['startup_delay']} seconds for startup...")
    sleep(CONFIG["server"]["startup_delay"])
    print_success("Server is ready!")

    return server_thread


def run_sandbox_demos(notereader_client, cds_client):
    """Run the sandbox demonstrations"""
    print_section("Running Sandbox Demonstrations", "🎭")

    # Start NoteReader demo
    print_step("Starting Clinical Documentation sandbox...")
    try:
        responses = notereader_client.send_requests()
        notereader_client.save_results("./output/")
        print_success(
            f"Clinical Documentation sandbox completed - {len(responses)} response(s)"
        )
    except Exception as e:
        print(f"❌ NoteReader sandbox error: {str(e)}")

    sleep(2)

    # Start CDS Hooks demo
    print_step("Starting Clinical Decision Support sandbox...")
    try:
        responses = cds_client.send_requests()
        cds_client.save_results("./output/")
        print_success(
            f"Clinical Decision Support sandbox completed - {len(responses)} response(s)"
        )
    except Exception as e:
        print(f"❌ CDS sandbox error: {str(e)}")


# FHIR Endpoint Validation Helpers
def check_metadata_endpoint(base_url: str) -> ValidationResult:
    """Check FHIR metadata endpoint accessibility"""
    print_step("Checking FHIR metadata endpoint...")

    response = make_api_request(f"{base_url}/fhir/metadata")
    if not response or response.status_code != 200:
        return ValidationResult(
            passed=False,
            message=f"Metadata endpoint returned status {response.status_code if response else 'no response'}",
            level=ValidationLevel.ERROR,
        )

    return ValidationResult(
        passed=True,
        message="FHIR metadata endpoint accessible",
        level=ValidationLevel.SUCCESS,
        details={"response": response.json()},
    )


def validate_capability_statement(metadata: dict) -> list[ValidationResult]:
    """Validate CapabilityStatement structure and content"""
    results = []

    # Check resource type
    if metadata.get("resourceType") != "CapabilityStatement":
        results.append(
            ValidationResult(
                passed=False,
                message=f"Expected CapabilityStatement, got {metadata.get('resourceType')}",
                level=ValidationLevel.WARNING,
            )
        )
        return results

    results.append(
        ValidationResult(
            passed=True,
            message="Valid FHIR CapabilityStatement returned",
            level=ValidationLevel.SUCCESS,
        )
    )

    # Check resource capabilities
    expected_resources = ["DocumentReference", "Patient"]
    rest_resources = metadata.get("rest", [])

    if rest_resources and rest_resources[0].get("resource"):
        actual_resources = [r["type"] for r in rest_resources[0]["resource"]]
        missing = set(expected_resources) - set(actual_resources)

        if not missing:
            results.append(
                ValidationResult(
                    passed=True,
                    message="All expected resources found in capability statement",
                    level=ValidationLevel.SUCCESS,
                    details={"📊 Supported resources": ", ".join(actual_resources)},
                )
            )
        else:
            results.append(
                ValidationResult(
                    passed=False,
                    message=f"Missing expected resources: {', '.join(missing)}",
                    level=ValidationLevel.WARNING,
                )
            )
    else:
        results.append(
            ValidationResult(
                passed=False,
                message="No resource capabilities found in statement",
                level=ValidationLevel.WARNING,
            )
        )

    # Check FHIR version
    if fhir_version := metadata.get("fhirVersion"):
        results.append(
            ValidationResult(
                passed=True,
                message=f"FHIR version: {fhir_version}",
                level=ValidationLevel.SUCCESS,
            )
        )

    # Check gateway information
    if gateways := metadata.get("gateways"):
        gateway_details = []
        for name, info in gateways.items():
            endpoints = info.get("endpoints", [])
            gateway_details.append(
                f"{name} ({info.get('type', 'Unknown')}): {len(endpoints)} endpoints"
            )

        results.append(
            ValidationResult(
                passed=True,
                message=f"CapabilityStatement includes {len(gateways)} gateway(s)",
                level=ValidationLevel.SUCCESS,
                details={"Gateways": gateway_details},
            )
        )

    return results


def check_gateway_status(base_url: str) -> list[ValidationResult]:
    """Check gateway status endpoint and validate structure"""
    print_step("Checking gateway status endpoint...")
    results = []

    response = make_api_request(f"{base_url}/fhir/status")
    if not response or response.status_code != 200:
        results.append(
            ValidationResult(
                passed=False,
                message=f"Status endpoint returned status {response.status_code if response else 'no response'}",
                level=ValidationLevel.ERROR,
            )
        )
        return results

    status = response.json()
    results.append(
        ValidationResult(
            passed=True,
            message="Gateway status endpoint accessible",
            level=ValidationLevel.SUCCESS,
        )
    )

    # Validate gateway type
    if status.get("gateway_type") != "FHIRGateway":
        results.append(
            ValidationResult(
                passed=False,
                message=f"Expected FHIRGateway, got {status.get('gateway_type')}",
                level=ValidationLevel.ERROR,
            )
        )
        return results

    results.append(
        ValidationResult(
            passed=True,
            message="Valid gateway status returned",
            level=ValidationLevel.SUCCESS,
        )
    )

    # Check operations
    if ops := status.get("supported_operations"):
        resource_count = len(ops.keys())
        transform_count = sum(
            1
            for operations in ops.values()
            for op in operations
            if op.get("type") == "transform"
        )
        aggregate_count = sum(
            1
            for operations in ops.values()
            for op in operations
            if op.get("type") == "aggregate"
        )
        total_operations = sum(len(operations) for operations in ops.values())

        operation_details = [
            f"🔄 Transform endpoints: {transform_count}",
            f"📊 Aggregate endpoints: {aggregate_count}",
        ]
        for resource_name, operations in ops.items():
            operation_types = [op.get("type") for op in operations]
            operation_details.append(
                f"└── {resource_name}: {', '.join(operation_types)}"
            )

        results.append(
            ValidationResult(
                passed=True,
                message=f"Gateway supports {resource_count} resources, {total_operations} operations",
                level=ValidationLevel.SUCCESS,
                details={"Operations": operation_details},
            )
        )

    # Check event system
    if events := status.get("events"):
        if events.get("enabled"):
            results.append(
                ValidationResult(
                    passed=True,
                    message="Event system enabled",
                    level=ValidationLevel.SUCCESS,
                )
            )
            if events.get("dispatcher_configured"):
                results.append(
                    ValidationResult(
                        passed=True,
                        message="Event dispatcher configured",
                        level=ValidationLevel.SUCCESS,
                    )
                )
            else:
                results.append(
                    ValidationResult(
                        passed=True,
                        message="Event dispatcher not configured (normal for demo)",
                        level=ValidationLevel.INFO,
                    )
                )
        else:
            results.append(
                ValidationResult(
                    passed=True,
                    message="Event system disabled",
                    level=ValidationLevel.INFO,
                )
            )

    # Check sources
    if sources := status.get("sources"):
        source_count = sources.get("count", 0)
        if source_count > 0:
            source_names = sources.get("names", [])
            results.append(
                ValidationResult(
                    passed=True,
                    message=f"📡 Connected FHIR sources: {source_count}",
                    level=ValidationLevel.INFO,
                    details={"Sources": source_names},
                )
            )

    # Check discovery endpoints
    if discovery := status.get("discovery_endpoints"):
        discovery_list = [
            f"{endpoint}: {description}" for endpoint, description in discovery.items()
        ]
        results.append(
            ValidationResult(
                passed=True,
                message=f"Gateway provides {len(discovery)} discovery endpoints",
                level=ValidationLevel.SUCCESS,
                details={"Endpoints": discovery_list},
            )
        )

    return results


def check_transform_endpoint(base_url: str) -> list[ValidationResult]:
    """Check DocumentReference transform endpoint"""
    print_step("Checking DocumentReference transform endpoint...")
    results = []

    response = make_api_request(
        f"{base_url}/fhir/transform/DocumentReference/test-doc-123?source=demo"
    )
    if not response or response.status_code != 200:
        results.append(
            ValidationResult(
                passed=False,
                message=f"Transform endpoint returned status {response.status_code if response else 'no response'}",
                level=ValidationLevel.ERROR,
            )
        )
        return results

    doc_data = response.json()
    results.append(
        ValidationResult(
            passed=True,
            message="Transform endpoint accessible",
            level=ValidationLevel.SUCCESS,
        )
    )

    # Validate response structure
    if doc_data.get("resourceType") != "DocumentReference":
        results.append(
            ValidationResult(
                passed=False,
                message=f"Expected DocumentReference, got {doc_data.get('resourceType')}",
                level=ValidationLevel.ERROR,
            )
        )
        return results

    results.append(
        ValidationResult(
            passed=True,
            message="Valid DocumentReference returned from transform",
            level=ValidationLevel.SUCCESS,
        )
    )

    # Check for AI enhancement
    extensions = doc_data.get("extension", [])
    ai_enhanced = any("ai-summary" in ext.get("url", "") for ext in extensions)

    if ai_enhanced:
        results.append(
            ValidationResult(
                passed=True,
                message="Document contains AI enhancement extension",
                level=ValidationLevel.SUCCESS,
            )
        )
    else:
        results.append(
            ValidationResult(
                passed=False,
                message="No AI enhancement extension found",
                level=ValidationLevel.WARNING,
            )
        )

    return results


def check_aggregate_endpoint(base_url: str) -> list[ValidationResult]:
    """Check Patient aggregate endpoint"""
    print_step("Checking Patient aggregate endpoint...")
    results = []

    response = make_api_request(
        f"{base_url}/fhir/aggregate/Patient?id=test-patient-123&sources=demo&sources=epic"
    )
    if not response or response.status_code != 200:
        results.append(
            ValidationResult(
                passed=False,
                message=f"Aggregate endpoint returned status {response.status_code if response else 'no response'}",
                level=ValidationLevel.ERROR,
            )
        )
        return results

    patient_data = response.json()
    results.append(
        ValidationResult(
            passed=True,
            message="Aggregate endpoint accessible",
            level=ValidationLevel.SUCCESS,
        )
    )

    # Validate response structure
    if patient_data.get("resourceType") != "Patient":
        results.append(
            ValidationResult(
                passed=False,
                message=f"Expected Patient, got {patient_data.get('resourceType')}",
                level=ValidationLevel.ERROR,
            )
        )
        return results

    results.append(
        ValidationResult(
            passed=True,
            message="Valid Patient returned from aggregate",
            level=ValidationLevel.SUCCESS,
        )
    )

    # Check patient has expected fields
    if patient_data.get("id") and patient_data.get("gender"):
        results.append(
            ValidationResult(
                passed=True,
                message="Patient contains expected demographic data",
                level=ValidationLevel.SUCCESS,
            )
        )
    else:
        results.append(
            ValidationResult(
                passed=False,
                message="Patient missing expected demographic fields",
                level=ValidationLevel.WARNING,
            )
        )

    return results


def validate_fhir_endpoints():
    """Validate that FHIR Gateway endpoints are properly registered"""
    print_section("Validating FHIR Gateway Endpoints", "🔍")

    base_url = f"http://{CONFIG['server']['host']}:{CONFIG['server']['port']}"

    # Check metadata endpoint
    result = check_metadata_endpoint(base_url)
    result.print()

    if result.passed:
        metadata = result.details.get("response", {})
        for validation_result in validate_capability_statement(metadata):
            validation_result.print()

    # Check gateway status
    for result in check_gateway_status(base_url):
        result.print()

    # Check transform endpoint
    for result in check_transform_endpoint(base_url):
        result.print()

    # Check aggregate endpoint
    for result in check_aggregate_endpoint(base_url):
        result.print()


def validate_json_response(file_path: str) -> list[ValidationResult]:
    """Validate JSON response file (CDS response)"""
    results = []
    print_step(f"Checking latest JSON response: {Path(file_path).name}")

    try:
        with open(file_path, "r") as f:
            content = f.read()

        try:
            data = json.loads(content)

            if "cards" not in data:
                results.append(
                    ValidationResult(
                        passed=False,
                        message="JSON file has unknown structure",
                        level=ValidationLevel.WARNING,
                    )
                )
                return results

            results.append(
                ValidationResult(
                    passed=True,
                    message="File has CDS response structure",
                    level=ValidationLevel.SUCCESS,
                )
            )

            # Check for card details
            cards = data.get("cards", [])
            has_details = any(
                card.get("detail") and len(card.get("detail", "").strip()) > 0
                for card in cards
            )

            results.append(
                ValidationResult(
                    passed=has_details,
                    message="CDS response contains card details ✓"
                    if has_details
                    else "CDS response missing card details",
                    level=ValidationLevel.SUCCESS
                    if has_details
                    else ValidationLevel.WARNING,
                )
            )

        except json.JSONDecodeError:
            results.append(
                ValidationResult(
                    passed=False,
                    message="File is not valid JSON",
                    level=ValidationLevel.ERROR,
                )
            )

    except Exception as e:
        results.append(
            ValidationResult(
                passed=False,
                message=f"Error reading file: {str(e)}",
                level=ValidationLevel.ERROR,
            )
        )

    return results


def validate_xml_response(file_path: str) -> list[ValidationResult]:
    """Validate XML response file (CDA response)"""
    results = []
    print_step(f"Checking latest XML response: {Path(file_path).name}")

    try:
        with open(file_path, "r") as f:
            content = f.read()

        # Check for expected code in CDA content
        has_code = "0006477" in content.lower()
        results.append(
            ValidationResult(
                passed=has_code,
                message="CDA response contains '0006477' ✓"
                if has_code
                else "CDA response does not contain '0006477'",
                level=ValidationLevel.SUCCESS if has_code else ValidationLevel.WARNING,
            )
        )

        # Check for basic CDA structure
        has_structure = (
            "<ClinicalDocument" in content and "</ClinicalDocument>" in content
        )
        results.append(
            ValidationResult(
                passed=has_structure,
                message="Valid CDA document structure"
                if has_structure
                else "Invalid or incomplete CDA document structure",
                level=ValidationLevel.SUCCESS
                if has_structure
                else ValidationLevel.WARNING,
            )
        )

    except Exception as e:
        results.append(
            ValidationResult(
                passed=False,
                message=f"Error reading file: {str(e)}",
                level=ValidationLevel.ERROR,
            )
        )

    return results


def validate_output_files():
    """Validate that output files contain expected content"""
    print_section("Validating Output Files", "📁")

    output_dir = "output/responses"

    # Check if output directory exists
    if not os.path.exists(output_dir):
        print_warning(f"Output directory {output_dir} does not exist")
        return

    # Find all sandbox response files
    json_files = glob.glob(f"{output_dir}/*_sandbox_*_response_0.json")
    xml_files = glob.glob(f"{output_dir}/*_sandbox_*_response_0.xml")

    if not json_files and not xml_files:
        print_warning(f"No sandbox response files found in {output_dir}")
        return

    # Get latest files by modification time
    all_files = json_files + xml_files
    all_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    print_success(f"Found {len(all_files)} sandbox response file(s)")

    # Validate latest JSON file
    latest_json = [f for f in all_files if f.endswith(".json")]
    if latest_json:
        for result in validate_json_response(latest_json[0]):
            result.print()

    # Validate latest XML file
    latest_xml = [f for f in all_files if f.endswith(".xml")]
    if latest_xml:
        for result in validate_xml_response(latest_xml[0]):
            result.print()

    # Summary
    print_step("Validation summary:")
    print(f"  📊 Total files: {len(all_files)}")
    print(f"  📄 JSON: {len(json_files)}, XML: {len(xml_files)}")
    if all_files:
        print(f"  🕒 Latest: {Path(all_files[0]).name}")


def check_captured_events() -> list[ValidationResult]:
    """Check events captured during demo execution"""
    results = []

    if not hasattr(setup_event_handlers, "captured_events"):
        results.append(
            ValidationResult(
                passed=False,
                message="Event capture system not initialized",
                level=ValidationLevel.WARNING,
            )
        )
        return results

    captured = setup_event_handlers.captured_events

    if not captured:
        results.append(
            ValidationResult(
                passed=False,
                message="No events were captured during demo execution",
                level=ValidationLevel.WARNING,
            )
        )
        return results

    # Count events by type
    notereader_events = len([e for e in captured if e[0] == "notereader"])
    global_events = len([e for e in captured if e[0] == "global"])

    results.append(
        ValidationResult(
            passed=True,
            message=f"Captured {len(captured)} events during demo execution",
            level=ValidationLevel.SUCCESS,
            details={
                "📋 NoteReader events": str(notereader_events),
                "🔔 Global events": str(global_events),
            },
        )
    )

    if notereader_events > 0:
        results.append(
            ValidationResult(
                passed=True,
                message="Event system working - events fired during normal operations ✓",
                level=ValidationLevel.SUCCESS,
            )
        )
    else:
        results.append(
            ValidationResult(
                passed=False,
                message="No NoteReader events captured during demos",
                level=ValidationLevel.WARNING,
            )
        )

    return results


def test_event_system():
    """Validate that the event system worked during normal operations"""
    print_section("Validating Event System", "📡")

    print_step("Checking events captured during demos...")

    try:
        for result in check_captured_events():
            result.print()
    except Exception as e:
        ValidationResult(
            passed=False,
            message=f"Error checking captured events: {str(e)}",
            level=ValidationLevel.ERROR,
        ).print()


def run_automated_validation():
    """Run all automated validation checks"""
    print_section("🔍 Automated Validation Suite", "🧪")
    print("Running automated checks to verify system functionality...")

    # Give the system a moment to settle after demos
    sleep(2)

    # Run all validation checks
    validate_fhir_endpoints()
    validate_output_files()
    test_event_system()

    print_section("Validation Complete", "✅")
    print("All automated checks completed. Review results above for any issues.")


def main():
    """Main demo orchestrator"""
    print_section("🏥 HealthChain Complete Sandbox Demo", "🎯")
    print(
        "Demonstrating the full HealthChain ecosystem with AI-powered healthcare workflows"
    )

    try:
        # Validate prerequisites first
        validate_prerequisites()

        # Setup
        setup_environment()
        setup_event_handlers()

        # Create components
        coding_pipeline, summarization_pipeline = create_pipelines()
        note_service, cds_service, fhir_gateway = create_services(
            coding_pipeline, summarization_pipeline
        )
        app = create_app(note_service, cds_service, fhir_gateway)
        notereader_sandbox, cds_sandbox = create_sandboxes()

        # Run demo
        server_thread = start_server(app)
        run_sandbox_demos(notereader_sandbox, cds_sandbox)

        # Run automated validation
        run_automated_validation()

        print_section("✨ Demo Complete", "🎉")
        print("All HealthChain components demonstrated and validated successfully!")
        print("Press Ctrl+C to stop the server")

        # Keep the server running
        try:
            server_thread.join()
        except KeyboardInterrupt:
            print("\n👋 Shutting down gracefully...")

    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
