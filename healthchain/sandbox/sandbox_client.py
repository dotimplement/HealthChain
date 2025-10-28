"""
SandboxClient for quickly spinning up demos and loading test datasets.

Replaces the decorator-based sandbox pattern with direct instantiation.
"""

from enum import Enum
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import httpx

from healthchain.models import CDSRequest, CDSResponse, Prefetch
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.sandbox.workflows import Workflow
from healthchain.sandbox.utils import ensure_directory_exists, save_data_to_directory


log = logging.getLogger(__name__)


class ApiProtocol(Enum):
    """
    Enum defining the supported API protocols.

    Available protocols:
    - soap: SOAP protocol
    - rest: REST protocol
    """

    soap = "SOAP"
    rest = "REST"


class SandboxClient:
    """
    Simplified client for testing healthcare services with various data sources.

    This class provides an intuitive interface for:
    - Loading test datasets (MIMIC-on-FHIR, Synthea, CSV)
    - Generating synthetic FHIR data
    - Sending requests to healthcare services
    - Managing request/response lifecycle

    Examples:
        Load from dataset registry:
        >>> client = SandboxClient(
        ...     api_url="http://localhost:8000",
        ...     endpoint="/cds/cds-services/my-service"
        ... )
        >>> client.load_from_registry("mimic-on-fhir", sample_size=10)
        >>> responses = client.send_requests()

        Load CDA file from path:
        >>> client = SandboxClient(
        ...     api_url="http://localhost:8000",
        ...     endpoint="/notereader/fhir/",
        ...     protocol="soap"
        ... )
        >>> client.load_from_path("./data/clinical_note.xml")
        >>> responses = client.send_requests()

        Generate data from free text:
        >>> client = SandboxClient(
        ...     api_url="http://localhost:8000",
        ...     endpoint="/cds/cds-services/discharge-summarizer"
        ... )
        >>> client.load_free_text(
        ...     csv_path="./data/notes.csv",
        ...     column_name="text",
        ...     workflow="encounter-discharge"
        ... )
        >>> responses = client.send_requests()
    """

    def __init__(
        self,
        api_url: str,
        endpoint: str,
        workflow: Optional[Union[Workflow, str]] = None,
        protocol: Literal["rest", "soap"] = "rest",
        timeout: float = 10.0,
    ):
        """
        Initialize SandboxClient.

        Args:
            api_url: Base URL of the service (e.g., "http://localhost:8000")
            endpoint: Service endpoint path (e.g., "/cds/cds-services/my-service")
            workflow: Optional workflow specification (auto-detected if not provided)
            protocol: Communication protocol - "rest" for CDS Hooks, "soap" for CDA
            timeout: Request timeout in seconds

        Raises:
            ValueError: If api_url or endpoint is invalid
        """
        try:
            self.api = httpx.URL(api_url)
        except Exception as e:
            raise ValueError(f"Invalid API URL: {str(e)}")

        self.endpoint = endpoint
        self.workflow = Workflow(workflow) if isinstance(workflow, str) else workflow
        self.protocol = ApiProtocol.soap if protocol == "soap" else ApiProtocol.rest
        self.timeout = timeout

        # Request/response management
        self.request_data: List[Union[CDSRequest, Any]] = []
        self.responses: List[Dict] = []
        self.sandbox_id = uuid.uuid4()

        log.info(
            f"Initialized SandboxClient {self.sandbox_id} for {self.api}{self.endpoint}"
        )

    def load_from_registry(
        self,
        source: str,
        **kwargs,
    ) -> "SandboxClient":
        """
        Load data from the dataset registry.

        Loads pre-configured datasets like MIMIC-on-FHIR, Synthea, or custom
        registered datasets.

        Args:
            source: Dataset name (e.g., "mimic-on-fhir", "synthea-patients")
            **kwargs: Dataset-specific parameters (e.g., sample_size, num_patients)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If dataset not found in registry

        Examples:
            Load MIMIC dataset:
            >>> client.load_from_registry("mimic-on-fhir", sample_size=10)

            Load Synthea dataset:
            >>> client.load_from_registry("synthea-patients", num_patients=5)
        """
        from healthchain.sandbox.datasets import DatasetRegistry

        log.info(f"Loading dataset from registry: {source}")
        try:
            loaded_data = DatasetRegistry.load(source, **kwargs)
            # TODO: check expected data format matches here
            self._construct_request(loaded_data)
            log.info(f"Loaded {source} dataset with {len(self.request_data)} requests")
        except KeyError:
            raise ValueError(
                f"Unknown dataset: {source}. "
                f"Available datasets: {DatasetRegistry.list_datasets()}"
            )
        return self

    def load_from_path(
        self,
        path: Union[str, Path],
        pattern: Optional[str] = None,
        workflow: Optional[Union[Workflow, str]] = None,
    ) -> "SandboxClient":
        """
        Load data from file system path.

        Supports loading single files or directories. File type is auto-detected
        from extension and protocol:
        - .xml files with SOAP protocol → CDA documents
        - .json files with REST protocol → FHIR bundles (future)

        Args:
            path: File path or directory path
            pattern: Glob pattern for filtering files in directory (e.g., "*.xml")
            workflow: Optional workflow override (auto-detected from protocol if not provided)

        Returns:
            Self for method chaining

        Raises:
            FileNotFoundError: If path doesn't exist
            ValueError: If no matching files found or unsupported file type

        Examples:
            Load single CDA file:
            >>> client.load_from_path("./data/clinical_note.xml")

            Load directory of CDA files:
            >>> client.load_from_path("./data/cda_files/", pattern="*.xml")

            Load with explicit workflow:
            >>> client.load_from_path("./data/note.xml", workflow="sign-note-inpatient")
        """
        from healthchain.fhir import create_document_reference

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        # Collect files to process
        files_to_load = []
        if path.is_file():
            files_to_load = [path]
        elif path.is_dir():
            pattern = pattern or "*"
            files_to_load = list(path.glob(pattern))
            if not files_to_load:
                raise ValueError(
                    f"No files found matching pattern '{pattern}' in {path}"
                )
        else:
            raise ValueError(f"Path must be a file or directory: {path}")

        log.info(f"Loading {len(files_to_load)} file(s) from {path}")

        # Process each file
        for file_path in files_to_load:
            # Determine file type from extension
            extension = file_path.suffix.lower()

            if extension == ".xml":
                # Load as CDA document
                with open(file_path, "r") as f:
                    xml_content = f.read()

                doc_ref = create_document_reference(
                    data=xml_content,
                    content_type="text/xml",
                    description=f"CDA document from {file_path.name}",
                )

                workflow_enum = (
                    Workflow(workflow)
                    if isinstance(workflow, str)
                    else workflow or self.workflow or Workflow.sign_note_inpatient
                )
                self._construct_request(doc_ref, workflow_enum)

            elif extension == ".json":
                # TODO: if it is json, load as is as prefetch (example prefetch data)
                raise NotImplementedError(
                    "JSON/FHIR bundle loading not yet implemented"
                )
            else:
                log.warning(f"Skipping unsupported file type: {file_path}")

        log.info(
            f"Loaded {len(self.request_data)} requests from {len(files_to_load)} file(s)"
        )
        return self

    def load_free_text(
        self,
        csv_path: str,
        column_name: str,
        workflow: Union[Workflow, str],
        random_seed: Optional[int] = None,
        **kwargs,
    ) -> "SandboxClient":
        """
        Generate synthetic FHIR data from free text notes using CdsDataGenerator.

        Reads clinical notes from a CSV file and generates complete FHIR resources
        (Patient, Encounter, etc.) around the text for CDS Hooks workflows.

        Args:
            csv_path: Path to CSV file containing clinical notes
            column_name: Name of the column containing the text
            workflow: CDS workflow type (e.g., "encounter-discharge", "patient-view")
            random_seed: Seed for reproducible data generation
            **kwargs: Additional parameters for data generation

        Returns:
            Self for method chaining

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If workflow is invalid or column not found

        Examples:
            Generate discharge summaries:
            >>> client.load_free_text(
            ...     csv_path="./data/discharge_notes.csv",
            ...     column_name="text",
            ...     workflow="encounter-discharge",
            ...     random_seed=42
            ... )

            Generate patient views:
            >>> client.load_free_text(
            ...     csv_path="./data/clinical_notes.csv",
            ...     column_name="note_text",
            ...     workflow="patient-view"
            ... )
        """
        from healthchain.data_generators import CdsDataGenerator

        workflow_enum = Workflow(workflow) if isinstance(workflow, str) else workflow

        log.info(
            f"Generating FHIR data from free text for workflow: {workflow_enum.value}"
        )

        generator = CdsDataGenerator()
        generator.set_workflow(workflow_enum)

        prefetch_data = generator.generate_prefetch(
            random_seed=random_seed,
            free_text_path=csv_path,
            column_name=column_name,
            **kwargs,
        )

        self._construct_request(prefetch_data, workflow_enum)
        log.info(f"Generated {len(self.request_data)} requests from free text")

        return self

    def _construct_request(
        self, data: Union[Prefetch, Any], workflow: Optional[Workflow] = None
    ) -> None:
        """
        Convert data to request format and add to queue.

        Args:
            data: Data to convert (Prefetch for CDS, DocumentReference for CDA)
            workflow: Workflow to use for request construction
        """
        from healthchain.sandbox.use_cases.cds import CdsRequestConstructor
        from healthchain.sandbox.use_cases.clindoc import ClinDocRequestConstructor

        workflow = workflow or self.workflow

        if self.protocol == ApiProtocol.rest:
            if not workflow:
                raise ValueError(
                    "Workflow must be specified for REST/CDS Hooks requests"
                )
            constructor = CdsRequestConstructor()
            request = constructor.construct_request(data, workflow)
        elif self.protocol == ApiProtocol.soap:
            constructor = ClinDocRequestConstructor()
            request = constructor.construct_request(
                data, workflow or Workflow.sign_note_inpatient
            )
        else:
            raise ValueError(f"Unsupported protocol: {self.protocol}")

        self.request_data.append(request)

    def send_requests(self) -> List[Dict]:
        """
        Send all queued requests to the service.

        Returns:
            List of response dictionaries

        Raises:
            RuntimeError: If no requests are queued
        """
        if not self.request_data:
            raise RuntimeError(
                "No requests to send. Load data first using load_from_registry(), load_from_path(), or load_free_text()"
            )

        url = self.api.join(self.endpoint)
        log.info(f"Sending {len(self.request_data)} requests to {url}")

        with httpx.Client(follow_redirects=True) as client:
            responses: List[Dict] = []
            timeout = httpx.Timeout(self.timeout, read=None)

            for request in self.request_data:
                try:
                    if self.protocol == ApiProtocol.soap:
                        headers = {"Content-Type": "text/xml; charset=utf-8"}
                        response = client.post(
                            url=str(url),
                            data=request.document,
                            headers=headers,
                            timeout=timeout,
                        )
                        response.raise_for_status()
                        response_model = CdaResponse(document=response.text)
                        responses.append(response_model.model_dump_xml())
                    else:
                        # REST/CDS Hooks
                        log.debug(f"Making POST request to: {url}")
                        response = client.post(
                            url=str(url),
                            json=request.model_dump(exclude_none=True),
                            timeout=timeout,
                        )
                        response.raise_for_status()
                        response_data = response.json()
                        try:
                            cds_response = CDSResponse(**response_data)
                            responses.append(cds_response.model_dump(exclude_none=True))
                        except Exception:
                            # Fallback to raw response if parsing fails
                            responses.append(response_data)

                except httpx.HTTPStatusError as exc:
                    try:
                        error_content = exc.response.json()
                    except Exception:
                        error_content = exc.response.text
                    log.error(
                        f"Error response {exc.response.status_code} while requesting "
                        f"{exc.request.url!r}: {error_content}"
                    )
                    responses.append({})
                except httpx.TimeoutException as exc:
                    log.error(f"Request to {exc.request.url!r} timed out!")
                    responses.append({})
                except httpx.RequestError as exc:
                    log.error(
                        f"An error occurred while requesting {exc.request.url!r}."
                    )
                    responses.append({})

        self.responses = responses
        log.info(f"Received {len(responses)} responses")
        return responses

    def save_responses(self, directory: Union[str, Path] = "./output/") -> None:
        """
        Save request and response data to disk.

        Args:
            directory: Directory to save data to (default: "./output/")

        Raises:
            RuntimeError: If no responses are available to save
        """
        if not self.responses:
            raise RuntimeError(
                "No responses to save. Send requests first using send_requests()"
            )

        save_dir = Path(directory)
        request_path = ensure_directory_exists(save_dir / "requests")

        # Determine file extension based on protocol
        extension = "xml" if self.protocol == ApiProtocol.soap else "json"

        # Save requests
        if self.protocol == ApiProtocol.soap:
            request_data = [request.model_dump_xml() for request in self.request_data]
        else:
            request_data = [
                request.model_dump(exclude_none=True) for request in self.request_data
            ]

        save_data_to_directory(
            request_data,
            "request",
            self.sandbox_id,
            request_path,
            extension,
        )
        log.info(f"Saved request data at {request_path}/")

        # Save responses
        response_path = ensure_directory_exists(save_dir / "responses")
        save_data_to_directory(
            self.responses,
            "response",
            self.sandbox_id,
            response_path,
            extension,
        )
        log.info(f"Saved response data at {response_path}/")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current client status and statistics.

        Returns:
            Dictionary containing client status information
        """
        return {
            "sandbox_id": str(self.sandbox_id),
            "api_url": str(self.api),
            "endpoint": self.endpoint,
            "protocol": self.protocol.value
            if hasattr(self.protocol, "value")
            else str(self.protocol),
            "workflow": self.workflow.value if self.workflow else None,
            "requests_queued": len(self.request_data),
            "responses_received": len(self.responses),
        }

    def __repr__(self) -> str:
        """String representation of SandboxClient."""
        return (
            f"SandboxClient(api_url='{self.api}', endpoint='{self.endpoint}', "
            f"protocol='{self.protocol.value if hasattr(self.protocol, 'value') else self.protocol}', "
            f"requests={len(self.request_data)})"
        )
