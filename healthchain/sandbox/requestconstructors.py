"""
Request constructors for different clinical integration protocols.

- CdsRequestConstructor: Builds CDS Hooks requests (REST/JSON)
- ClinDocRequestConstructor: Builds NoteReader requests (SOAP/XML)
"""

import logging
import base64
import pkgutil
import xmltodict

from typing import Any, Dict, Optional

from healthchain.sandbox.base import BaseRequestConstructor, ApiProtocol
from healthchain.sandbox.workflows import (
    UseCaseMapping,
    Workflow,
    validate_workflow,
)
from healthchain.models.requests import CDSRequest
from healthchain.models import CdaRequest
from healthchain.utils.utils import insert_at_key
from healthchain.models.hooks import (
    OrderSelectContext,
    OrderSignContext,
    PatientViewContext,
    EncounterDischargeContext,
)


log = logging.getLogger(__name__)


class CdsRequestConstructor(BaseRequestConstructor):
    """
    Constructs and validates CDS Hooks requests for Clinical Decision Support (CDS) workflows.

    This class facilitates building HL7-compliant CDS Hooks requests for use with the REST API.
    It supports multiple standard CDS workflows (e.g., patient-view, order-select, etc.) and
    verifies both input workflow and prefetch data integrity.

    Attributes:
        api_protocol (ApiProtocol): Specifies the supported API protocol (REST).
        context_mapping (dict): Maps supported Workflow enums to their context model classes.
    """

    def __init__(self) -> None:
        self.api_protocol = ApiProtocol.rest
        self.context_mapping = {
            Workflow.order_select: OrderSelectContext,
            Workflow.order_sign: OrderSignContext,
            Workflow.patient_view: PatientViewContext,
            Workflow.encounter_discharge: EncounterDischargeContext,
        }

    @validate_workflow(UseCaseMapping.ClinicalDecisionSupport)
    def construct_request(
        self,
        prefetch_data: Dict[str, Any],
        workflow: Workflow,
        context: Optional[Dict[str, str]] = {},
    ) -> CDSRequest:
        """
        Build a CDS Hooks request including context and prefetch data.

        Args:
            prefetch_data (Dict[str, Any]): Dict containing FHIR resource objects.
            workflow (Workflow): The name of the CDS Hooks workflow (e.g., Workflow.patient_view).
            context (Optional[Dict[str, str]]): Optional context values for initializing the workflow's context model.

        Returns:
            CDSRequest: Pydantic model representing a well-formed CDS Hooks request.

        Raises:
            ValueError: If the workflow is not supported or lacks a defined context model.

        Note:
            Only CDS workflows supported by UseCaseMapping.ClinicalDecisionSupport are valid.

        # TODO: Add FhirServer support in future.
        """

        log.debug(f"Constructing CDS request for {workflow.value}")

        context_model = self.context_mapping.get(workflow, None)
        if context_model is None:
            raise ValueError(
                f"Invalid workflow {workflow.value} or workflow model not implemented."
            )

        request = CDSRequest(
            hook=workflow.value,
            context=context_model(**context),
            prefetch=prefetch_data,
        )
        return request


class ClinDocRequestConstructor(BaseRequestConstructor):
    """
    Constructs and validates CDA-based clinical documentation requests for NoteReader workflows.

    This constructor handles the preparation of a SOAP envelope containing a base64-encoded CDA XML document,
    suitable for clinical documentation use cases (e.g., 'sign-note-inpatient', 'sign-note-outpatient').
    It ensures the input XML is valid, encodes it, and inserts it into the expected place within a SOAP envelope
    template, producing a structured `CdaRequest` model for downstream processing or transmission.

    Attributes:
        api_protocol (ApiProtocol): The protocol used for API communication (SOAP).
        soap_envelope (Dict): Loaded SOAP envelope template as a dictionary.

    Methods:
        construct_cda_xml_document():
            Not implemented. Intended to wrap FHIR Document resources into a CDA XML document.
        construct_request(data: str, workflow: Workflow) -> CdaRequest:
            Validates and encodes the input CDA XML, inserts it into the SOAP envelope,
            and returns a structured CdaRequest object.
    """

    def __init__(self) -> None:
        self.api_protocol: ApiProtocol = ApiProtocol.soap
        self.soap_envelope: Dict = self._load_soap_envelope()

    def _load_soap_envelope(self):
        data = pkgutil.get_data("healthchain", "templates/soap_envelope.xml")
        return xmltodict.parse(data.decode("utf-8"))

    def construct_cda_xml_document(self):
        """
        Placeholder for CDA construction logic.

        This function should take FHIR resources and construct a CDA XML document
        using a suitable template. Currently not implemented.
        """
        raise NotImplementedError("This function is not implemented yet.")

    @validate_workflow(UseCaseMapping.ClinicalDocumentation)
    def construct_request(self, data: str, workflow: Workflow) -> CdaRequest:
        """
        Construct a CdaRequest for clinical documentation workflows.

        This method creates a request containing the input CDA XML string wrapped in a SOAP envelope.
        It validates that the input is a well-formed XML string, base64-encodes it,
        and embeds it at the appropriate location in the SOAP envelope template.

        Args:
            data (str): The raw CDA XML document as a string.
            workflow (Workflow): The workflow type for the documentation use case (e.g., sign-note-inpatient).

        Returns:
            CdaRequest: A model containing the finalized SOAP envelope with the base64-encoded CDA XML.

        Raises:
            ValueError: If the input is not a string, or if the SOAP template is missing required keys.
            None: If the input XML is not valid (logs a warning and returns None).

        Note:
            This method does not implement workflow-specific logic. Extend if such handling is required.
        """
        # TODO: Add workflow-specific handling if needed
        if not isinstance(data, str):
            raise ValueError(f"Expected str, got {type(data).__name__}")

        # Validate that the string is well-formed XML
        import xml.etree.ElementTree as ET

        try:
            ET.fromstring(data)
        except ET.ParseError as e:
            log.warning("Input is not valid XML: %s", e)
            return None

        # Make a copy of the SOAP envelope template
        soap_envelope = self.soap_envelope.copy()

        # Base64 encode the XML
        cda_xml_encoded = base64.b64encode(data.encode("utf-8")).decode("utf-8")

        # Insert encoded cda in the Document section
        if not insert_at_key(soap_envelope, "urn:Document", cda_xml_encoded):
            raise ValueError("Key 'urn:Document' missing from SOAP envelope template!")

        request = CdaRequest.from_dict(soap_envelope)

        return request
