"""
SandboxClient for quickly spinning up demos and loading test datasets.

Replaces the decorator-based sandbox pattern with direct instantiation.
"""

import json
import logging
import uuid
import httpx

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from healthchain.sandbox.base import ApiProtocol
from healthchain.models import CDSRequest, CDSResponse
from healthchain.models.responses.cdaresponse import CdaResponse
from healthchain.sandbox.workflows import Workflow
from healthchain.sandbox.utils import ensure_directory_exists, save_data_to_directory
from healthchain.sandbox.requestconstructors import (
    CdsRequestConstructor,
    ClinDocRequestConstructor,
)


log = logging.getLogger(__name__)


class SandboxClient:
    """
    Simplified client for testing healthcare services with various data sources.

    This class provides an intuitive interface for:
    - Loading test datasets (MIMIC-on-FHIR, Synthea)
    - Generating synthetic FHIR data
    - Sending requests to healthcare services
    - Managing request/response lifecycle

    Examples:
        Load from dataset registry:
        >>> client = SandboxClient(
        ...     url="http://localhost:8000/cds/cds-services/my-service"
        ... )
        >>> client.load_from_registry("mimic-on-fhir", sample_size=10)
        >>> responses = client.send_requests()

        Load CDA file from path:
        >>> client = SandboxClient(
        ...     url="http://localhost:8000/notereader/?wsdl",
        ...     protocol="soap"
        ... )
        >>> client.load_from_path("./data/clinical_note.xml")
        >>> responses = client.send_requests()

        Generate data from free text:
        >>> client = SandboxClient(
        ...     url="http://localhost:8000/cds/cds-services/discharge-summarizer"
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
        url: str,
        workflow: Union[Workflow, str],
        protocol: Literal["rest", "soap"] = "rest",
        timeout: float = 10.0,
    ):
        """
        Initialize SandboxClient.

        Args:
            url: Full service URL (e.g., "http://localhost:8000/cds/cds-services/my-service")
            workflow: Workflow specification (required) - determines request type and validation
            protocol: Communication protocol - "rest" for CDS Hooks, "soap" for CDA
            timeout: Request timeout in seconds

        Raises:
            ValueError: If url or workflow-protocol combination is invalid
        """
        try:
            self.url = httpx.URL(url)
        except Exception as e:
            raise ValueError(f"Invalid URL: {str(e)}")

        self.workflow = Workflow(workflow) if isinstance(workflow, str) else workflow
        self.protocol = ApiProtocol.soap if protocol == "soap" else ApiProtocol.rest
        self.timeout = timeout

        # Request/response management
        self.requests: List[Union[CDSRequest, Any]] = []
        self.responses: List[Dict] = []
        self.sandbox_id = uuid.uuid4()

        # Single validation point - fail fast on incompatible workflow-protocol
        self._validate_workflow_protocol()

        log.info(f"Initialized SandboxClient {self.sandbox_id} for {self.url}")

    def _validate_workflow_protocol(self) -> None:
        """
        Validate workflow is compatible with protocol.

        Raises:
            ValueError: If workflow-protocol combination is invalid
        """
        from healthchain.sandbox.workflows import UseCaseMapping

        if self.protocol == ApiProtocol.soap:
            # SOAP only works with ClinicalDocumentation workflows
            soap_workflows = UseCaseMapping.ClinicalDocumentation.allowed_workflows
            if self.workflow.value not in soap_workflows:
                raise ValueError(
                    f"Workflow '{self.workflow.value}' is not compatible with SOAP protocol. "
                    f"SOAP requires Clinical Documentation workflows: {soap_workflows}"
                )

        elif self.protocol == ApiProtocol.rest:
            # REST only works with CDS workflows
            rest_workflows = UseCaseMapping.ClinicalDecisionSupport.allowed_workflows
            if self.workflow.value not in rest_workflows:
                raise ValueError(
                    f"Workflow '{self.workflow.value}' is not compatible with REST protocol. "
                    f"REST requires CDS workflows: {rest_workflows}"
                )

    def load_from_registry(
        self,
        source: str,
        data_dir: str,
        **kwargs: Any,
    ) -> "SandboxClient":
        """
        Load data from the dataset registry.

        Loads pre-configured datasets like MIMIC-on-FHIR, Synthea, or custom
        registered datasets.

        Args:
            source: Dataset name (e.g., "mimic-on-fhir", "synthea")
            data_dir: Path to the dataset directory
            **kwargs: Dataset-specific parameters (e.g., resource_types, sample_size)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If dataset not found in registry
            FileNotFoundError: If data_dir doesn't exist

        Examples:
            Load MIMIC dataset:
            >>> client = SandboxClient(
            ...     url="http://localhost:8000/cds/patient-view",
            ...     workflow="patient-view",
            ... )
            >>> client.load_from_registry(
            ...     "mimic-on-fhir",
            ...     data_dir="./data/mimic-fhir",
            ...     resource_types=["MimicMedication"],
            ...     sample_size=10
            ... )
        """
        from healthchain.sandbox.datasets import DatasetRegistry

        log.info(f"Loading dataset from registry: {source}")
        try:
            loaded_data = DatasetRegistry.load(source, data_dir=data_dir, **kwargs)
            self._construct_request(loaded_data)
            log.info(f"Loaded {source} dataset with {len(self.requests)} requests")
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
    ) -> "SandboxClient":
        """
        Load data from a file or directory.

        Supports single files or all matching files in a directory (with optional glob pattern).
        For .xml (SOAP protocol) loads CDA; for .json (REST protocol) loads Prefetch.

        Args:
            path: File or directory path.
            pattern: Glob pattern for files in directory (e.g., "*.xml").

        Returns:
            Self.

        Raises:
            FileNotFoundError: If path does not exist.
            ValueError: If no matching files are found or if path is not file/dir.
        """

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
                with open(file_path, "r") as f:
                    xml_content = f.read()
                self._construct_request(xml_content)
                log.info(f"Loaded CDA document from {file_path.name}")

            elif extension == ".json":
                with open(file_path, "r") as f:
                    json_data = json.load(f)

                try:
                    self._construct_request(json_data)
                    log.info(f"Loaded prefetch data from {file_path.name}")

                except Exception as e:
                    log.error(f"Failed to parse {file_path} as prefetch data: {e}")
                    raise ValueError(
                        f"File {file_path} is not valid prefetch format. "
                        f"Expected JSON with FHIR resources. "
                        f"Error: {e}"
                    )
            else:
                log.warning(f"Skipping unsupported file type: {file_path}")

        log.info(
            f"Loaded {len(self.requests)} requests from {len(files_to_load)} file(s)"
        )
        return self

    def load_free_text(
        self,
        csv_path: str,
        column_name: str,
        generate_synthetic: bool = True,
        random_seed: Optional[int] = None,
        **kwargs: Any,
    ) -> "SandboxClient":
        """
        Load free-text notes from a CSV column and create FHIR DocumentReferences for CDS prefetch.
        Optionally include synthetic FHIR resources based on the current workflow.

        Args:
            csv_path: Path to the CSV file
            column_name: Name of the text column
            generate_synthetic: Whether to add synthetic FHIR resources (default: True)
            random_seed: Seed for reproducible results
            **kwargs: Extra parameters for data generation

        Returns:
            self

        Raises:
            FileNotFoundError: If the CSV file does not exist
            ValueError: If the column is not found
        """
        from .generators import CdsDataGenerator

        generator = CdsDataGenerator()
        generator.set_workflow(self.workflow)

        prefetch_data = generator.generate_prefetch(
            random_seed=random_seed,
            free_text_path=csv_path,
            column_name=column_name,
            generate_resources=generate_synthetic,
            **kwargs,
        )

        self._construct_request(prefetch_data)

        if generate_synthetic:
            log.info(
                f"Generated {len(self.requests)} requests from free text with synthetic resources for workflow {self.workflow.value}"
            )
        else:
            log.info(
                f"Generated {len(self.requests)} requests from free text only (no synthetic resources)"
            )

        return self

    def _construct_request(self, data: Union[Dict[str, Any], Any]) -> None:
        """
        Convert data to request format and add to queue.

        Args:
            data: Data to convert (Dict for CDS prefetch, string for CDA)
        """
        if self.protocol == ApiProtocol.rest:
            constructor = CdsRequestConstructor()
            request = constructor.construct_request(data, self.workflow)
        elif self.protocol == ApiProtocol.soap:
            constructor = ClinDocRequestConstructor()
            request = constructor.construct_request(data, self.workflow)
        else:
            raise ValueError(f"Unsupported protocol: {self.protocol}")

        self.requests.append(request)

    def clear_requests(self) -> "SandboxClient":
        """
        Clear all queued requests.

        Useful when you want to start fresh without creating a new client instance.

        Returns:
            Self for method chaining
        """
        count = len(self.requests)
        self.requests.clear()
        log.info(f"Cleared {count} queued request(s)")

        return self

    def preview_requests(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get preview of queued requests without sending them.

        Provides a summary view of what requests are queued, useful for debugging
        and verifying data was loaded correctly before sending.

        Args:
            limit: Maximum number of requests to preview. If None, preview all.

        Returns:
            List of request summary dictionaries containing metadata
        """
        requests = self.requests[:limit] if limit else self.requests
        previews = []

        for idx, req in enumerate(requests):
            preview = {
                "index": idx,
                "type": req.__class__.__name__,
                "protocol": self.protocol.value
                if hasattr(self.protocol, "value")
                else str(self.protocol),
            }

            # Add protocol-specific info
            if self.protocol == ApiProtocol.rest and hasattr(req, "hook"):
                preview["hook"] = req.hook
                preview["hookInstance"] = getattr(req, "hookInstance", None)
            elif self.protocol == ApiProtocol.soap:
                preview["has_document"] = hasattr(req, "document")

            previews.append(preview)

        return previews

    def get_request_data(
        self, format: Literal["dict", "json"] = "dict"
    ) -> Union[List[Dict], str]:
        """
        Get transformed request data for inspection.

        Allows access to serialized request data for debugging or custom processing.
        For direct access to Pydantic models, use the `requests` attribute:
            >>> for request in client.requests:
            >>>     print(request.model_dump())

        Args:
            format: Return format - "dict" for list of dictionaries,
                   "json" for JSON string

        Returns:
            Request data in specified format

        Raises:
            ValueError: If format is not "dict" or "json"

        Examples:
            >>> client.load_from_path("data.xml")
            >>> # Access raw Pydantic models directly
            >>> for request in client.requests:
            >>>     print(request.model_dump(exclude_none=True))
            >>> # Get as dictionaries
            >>> dicts = client.get_request_data("dict")
            >>> # Get as JSON string
            >>> json_str = client.get_request_data("json")
            >>> print(json_str)
        """
        if format == "dict":
            result = []
            for req in self.requests:
                if hasattr(req, "model_dump"):
                    result.append(req.model_dump(exclude_none=True))
                elif hasattr(req, "model_dump_xml"):
                    result.append({"document": req.model_dump_xml()})
                else:
                    result.append(req)
            return result
        elif format == "json":
            return json.dumps(self.get_request_data("dict"), indent=2)
        else:
            raise ValueError(
                f"Invalid format '{format}'. Must be 'dict' or 'json'. "
                f"For raw Pydantic models, access the 'requests' attribute directly."
            )

    def send_requests(self) -> List[Dict]:
        """
        Send all queued requests to the service.

        Returns:
            List of response dictionaries
        """
        if not self.requests:
            raise RuntimeError(
                "No requests to send. Load data first using load_from_registry(), load_from_path(), or load_free_text()"
            )

        log.info(f"Sending {len(self.requests)} requests to {self.url}")

        with httpx.Client(follow_redirects=True) as client:
            responses: List[Dict] = []
            timeout = httpx.Timeout(self.timeout, read=None)

            for request in self.requests:
                try:
                    if self.protocol == ApiProtocol.soap:
                        headers = {"Content-Type": "text/xml; charset=utf-8"}
                        response = client.post(
                            url=str(self.url),
                            data=request.document,
                            headers=headers,
                            timeout=timeout,
                        )
                        response.raise_for_status()
                        response_model = CdaResponse(document=response.text)
                        responses.append(response_model.model_dump_xml())
                    else:
                        # REST/CDS Hooks
                        log.debug(f"Making POST request to: {self.url}")
                        response = client.post(
                            url=str(self.url),
                            json=request.model_dump(exclude_none=True, mode="json"),
                            timeout=timeout,
                        )
                        response.raise_for_status()

                        try:
                            response_data = response.json()
                            cds_response = CDSResponse(**response_data)
                            responses.append(
                                cds_response.model_dump(mode="json", exclude_none=True)
                            )
                        except json.JSONDecodeError:
                            log.error(
                                f"Invalid JSON response from {self.url}. "
                                f"Response preview: {response.text[:200]}"
                            )
                            responses.append({})
                        except Exception:
                            # Fallback to raw response if CDSResponse parsing fails
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

    def save_results(
        self,
        directory: Union[str, Path] = "./output/",
        save_request: bool = True,
        save_response: bool = True,
    ) -> None:
        """
        Save request and/or response data to disk.

        Args:
            directory: Directory to save data to (default: "./output/")
            save_request: Whether to save request data (default: True)
            save_response: Whether to save response data (default: True)
        """
        if not self.responses and save_response:
            raise RuntimeError(
                "No responses to save. Send requests first using send_requests()"
            )

        save_dir = Path(directory)
        extension = "xml" if self.protocol == ApiProtocol.soap else "json"

        if save_request:
            request_path = ensure_directory_exists(save_dir / "requests")
            if self.protocol == ApiProtocol.soap:
                request_data = [request.model_dump_xml() for request in self.requests]
            else:
                request_data = [
                    request.model_dump(mode="json", exclude_none=True)
                    for request in self.requests
                ]
            save_data_to_directory(
                request_data,
                "request",
                self.sandbox_id,
                request_path,
                extension,
            )
            log.info(f"Saved request data at {request_path}/")

        if save_response:
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
            "url": str(self.url),
            "protocol": self.protocol.value
            if hasattr(self.protocol, "value")
            else str(self.protocol),
            "workflow": self.workflow.value if self.workflow else None,
            "requests_queued": len(self.requests),
            "responses_received": len(self.responses),
        }

    def __enter__(self) -> "SandboxClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit - auto-save results if responses exist.

        Only saves if no exception occurred and responses were generated.
        """
        if self.responses and exc_type is None:
            try:
                self.save_results()
                log.info("Auto-saved results on context exit")
            except Exception as e:
                log.warning(f"Failed to auto-save results: {e}")

    def __repr__(self) -> str:
        """String representation of SandboxClient."""
        return (
            f"SandboxClient(url='{self.url}', "
            f"protocol='{self.protocol.value if hasattr(self.protocol, 'value') else self.protocol}', "
            f"requests={len(self.requests)})"
        )
