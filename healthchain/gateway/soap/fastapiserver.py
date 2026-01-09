# fastapiserver.py
from fastapi import APIRouter, Request, Response
import lxml.etree as ET
from typing import Callable, Optional, Any, Dict
from healthchain.models.requests.cdarequest import CdaRequest
from healthchain.models.responses.cdaresponse import CdaResponse
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# SOAP namespace for envelope
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
NSMAP = {"soap": SOAP_NS}

# WSDL target namespace (from your WSDL)
WSDL_NS = "urn:epic-com:Common.2013.Services"


def build_soap_envelope(body_xml: ET._Element) -> bytes:
    """
    Wrap the provided body element in a SOAP Envelope/Body and return bytes.
    The body_xml element should already be namespaced (if desired).
    """
    # Define namespace map with tns prefix for the WSDL namespace
    nsmap = {"soap": SOAP_NS, "tns": WSDL_NS}
    envelope = ET.Element(ET.QName(SOAP_NS, "Envelope"), nsmap=nsmap)
    body = ET.SubElement(envelope, ET.QName(SOAP_NS, "Body"))
    body.append(body_xml)
    return ET.tostring(envelope, xml_declaration=True, encoding="utf-8")


def build_soap_fault(faultcode: str, faultstring: str) -> bytes:
    """
    Construct a SOAP Fault element and return the full SOAP envelope bytes.
    """
    # Fault must be in the Body, not namespaced by the WSDL
    fault = ET.Element("Fault")
    code_el = ET.SubElement(fault, "faultcode")
    code_el.text = faultcode
    string_el = ET.SubElement(fault, "faultstring")
    string_el.text = faultstring
    return build_soap_envelope(fault)


def safe_text_of(el: ET._Element) -> Optional[str]:
    """
    Return the text content of an element.

    If the element has child elements (like Document containing XML),
    serialize the children as a string. Otherwise return the text content.
    """
    if el is None:
        return None

    # Check if element has child elements
    if len(el) > 0:
        # Element has children - serialize them as XML
        # This handles cases like <Document><xml>...</xml></Document>
        children_xml = []
        for child in el:
            children_xml.append(ET.tostring(child, encoding="unicode"))
        if children_xml:
            return "".join(children_xml)

    # No children - just get text content
    text = el.text if el.text is not None else None
    # Also check if text is just whitespace
    if text and text.strip():
        return text.strip()

    return None


def coerce_document_value(raw_val: Any) -> Optional[str]:
    """
    Accept a few possible document representations and return a string XML payload.
    - If raw_val is bytes -> decode as utf-8
    - If raw_val is a list -> use first element
    - If raw_val looks like base64 -> decode
    - If already a string -> return as-is
    """
    if raw_val is None:
        return None

    # if list, take first element
    if isinstance(raw_val, (list, tuple)) and len(raw_val) > 0:
        return coerce_document_value(raw_val[0])

    if isinstance(raw_val, bytes):
        try:
            return raw_val.decode("utf-8")
        except Exception:
            # try base64 decode
            try:
                decoded = base64.b64decode(raw_val)
                return decoded.decode("utf-8")
            except Exception:
                return raw_val.decode("latin1", errors="ignore")

    if isinstance(raw_val, str):
        text = raw_val.strip()

        # First check if it looks like XML
        if text.startswith("<"):
            return text

        # Heuristic: if looks like base64 (A-Z,a-z,0-9,+,/ and length multiple of 4)
        # and is longer than 20 chars
        bchars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        )
        if len(text) > 20 and all(c in bchars for c in text) and len(text) % 4 == 0:
            try:
                decoded = base64.b64decode(text)
                # If decode yields bytes that look like XML/utf-8, return that
                try:
                    decoded_str = decoded.decode("utf-8")
                    if decoded_str.strip().startswith("<"):
                        return decoded_str
                    # Otherwise return original
                    return text
                except Exception:
                    # fallback to returning original string
                    return text
            except Exception:
                return text
        return text

    # fallback
    return str(raw_val)


def create_fastapi_soap_router(
    service_name: str,
    namespace: str,
    handler: Callable[[CdaRequest], CdaResponse],
    wsdl_path: Optional[str] = None,
) -> APIRouter:
    """
    Create an APIRouter that exposes a SOAP endpoint for the ProcessDocument operation.

    - Expects SOAP document-style (per WSDL).
    - Handles Operation: ProcessDocument
    - Maps incoming element names (SessionID, WorkType, OrganizationID, Document)
      to CdaRequest fields (session_id, work_type, organization_id, document).
    - Returns ProcessDocumentResponse (Document, Error) wrapped in SOAP envelope.
    - Returns SOAP Faults for client/server errors.
    - Optionally serves WSDL at ?wsdl endpoint

    Args:
        service_name: Name of the SOAP service
        namespace: Target namespace for SOAP messages
        handler: Handler function for ProcessDocument operation
        wsdl_path: Optional path to WSDL file to serve
    """

    router = APIRouter()

    # Add WSDL endpoint if path provided
    if wsdl_path:

        @router.get("/")
        async def get_wsdl(request: Request):
            """Serve WSDL when ?wsdl query parameter is present"""
            if "wsdl" in request.query_params:
                try:
                    wsdl_file = Path(wsdl_path)
                    if not wsdl_file.exists():
                        logger.error(f"WSDL file not found: {wsdl_path}")
                        return Response(content="WSDL file not found", status_code=404)

                    wsdl_content = wsdl_file.read_text(encoding="utf-8")

                    # Replace placeholder location with actual server URL
                    base_url = str(request.base_url).rstrip("/")
                    path = request.url.path.rstrip("/")
                    actual_location = f"{base_url}{path}"

                    # Replace the location in WSDL
                    wsdl_content = wsdl_content.replace(
                        "{{SERVICE_LOCATION}}", actual_location
                    )

                    return Response(
                        content=wsdl_content, media_type="text/xml; charset=utf-8"
                    )
                except Exception:
                    logger.exception("Error serving WSDL")
                    return Response(
                        content="An internal error has occurred while serving WSDL.",
                        status_code=500,
                    )

    @router.post("/", summary=f"{service_name} SOAP entrypoint")
    async def soap_entrypoint(request: Request):
        raw = await request.body()
        try:
            parser = ET.XMLParser(resolve_entities=False)
            xml = ET.fromstring(raw, parser=parser)
        except ET.XMLSyntaxError as e:
            logger.exception("Invalid XML received")
            return Response(
                content=build_soap_fault("Client", f"Invalid XML: {str(e)}"),
                media_type="text/xml; charset=utf-8",
                status_code=400,
            )

        # Find Body
        body = xml.find("soap:Body", namespaces=NSMAP)
        if body is None or len(body) == 0:
            return Response(
                content=build_soap_fault("Client", "Missing SOAP Body"),
                media_type="text/xml; charset=utf-8",
                status_code=400,
            )

        # The operation element (document style) should be the first child of Body
        operation_el = body[0]
        # operation local name (strip namespace if present)
        operation_name = operation_el.tag.split("}")[-1]

        if operation_name != "ProcessDocument":
            return Response(
                content=build_soap_fault(
                    "Client", f"Unknown operation: {operation_name}"
                ),
                media_type="text/xml; charset=utf-8",
                status_code=400,
            )

        # Extract fields (namespace-agnostic)
        soap_params: Dict[str, Optional[str]] = {}
        for child in operation_el:
            local = child.tag.split("}")[-1]
            soap_params[local] = safe_text_of(child)

        logger.info(f"Received SOAP request with params: {list(soap_params.keys())}")

        # Map WSDL element names to CdaRequest field names
        # WSDL: SessionID, WorkType, OrganizationID, Document
        mapped = {
            "session_id": soap_params.get("SessionID"),
            "work_type": soap_params.get("WorkType"),
            "organization_id": soap_params.get("OrganizationID"),
            # Document may be large; attempt to coerce/ decode various forms
            "document": coerce_document_value(soap_params.get("Document")),
        }

        # Validate minimal required fields
        missing = []
        if not mapped["session_id"]:
            missing.append("SessionID")
        if not mapped["work_type"]:
            missing.append("WorkType")
        if not mapped["organization_id"]:
            missing.append("OrganizationID")
        if not mapped["document"]:
            missing.append("Document")

        if missing:
            return Response(
                content=build_soap_fault(
                    "Client", f"Missing required parameter(s): {', '.join(missing)}"
                ),
                media_type="text/xml; charset=utf-8",
                status_code=400,
            )

        # Build CdaRequest pydantic model
        try:
            request_obj = CdaRequest(
                session_id=mapped["session_id"],
                work_type=mapped["work_type"],
                organization_id=mapped["organization_id"],
                document=mapped["document"],
            )
        except Exception as e:
            logger.exception("Failed to construct CdaRequest")
            return Response(
                content=build_soap_fault(
                    "Client", f"Invalid request parameters: {str(e)}"
                ),
                media_type="text/xml; charset=utf-8",
                status_code=400,
            )

        # Call the provided handler (user-provided ProcessDocument function)
        try:
            resp_obj = handler(request_obj)
            logger.info(
                f"Handler returned response: document_length={len(resp_obj.document) if resp_obj.document else 0}, error={resp_obj.error}"
            )

            # IMPORTANT: Response Document must be base64-encoded per protocol
            # Check if handler returned plain text or already-encoded base64
            if resp_obj.document and isinstance(resp_obj.document, str):
                # Try to decode as base64 to test if it's already encoded
                is_already_base64 = False
                try:
                    # If this succeeds, it's valid base64
                    base64.b64decode(resp_obj.document, validate=True)
                    is_already_base64 = True
                    logger.info("Document is already base64-encoded")
                except Exception:
                    # Not valid base64, need to encode it
                    pass

                if not is_already_base64:
                    # Encode the plain text to base64
                    resp_obj.document = base64.b64encode(
                        resp_obj.document.encode("utf-8")
                    ).decode("ascii")
                    logger.info("Encoded plain text document to base64")

        except Exception as e:
            logger.exception("Handler threw exception")
            # Server fault
            return Response(
                content=build_soap_fault(
                    "Server", f"Server error processing request: {str(e)}"
                ),
                media_type="text/xml; charset=utf-8",
                status_code=500,
            )

        # Convert response object to SOAP response element
        # IMPORTANT: Match Spyne WSDL structure WITH ProcessDocumentResult wrapper!
        # <tns:ProcessDocumentResponse>
        #   <tns:ProcessDocumentResult>
        #     <tns:Document>base64string</tns:Document>
        #     <tns:Error>string</tns:Error>
        #   </tns:ProcessDocumentResult>
        # </tns:ProcessDocumentResponse>

        # Create response with explicit namespace map including tns prefix
        nsmap_response = {"tns": namespace}
        resp_el = ET.Element(
            ET.QName(namespace, "ProcessDocumentResponse"), nsmap=nsmap_response
        )

        # Add the ProcessDocumentResult wrapper (required by Spyne WSDL)
        result_wrapper = ET.SubElement(
            resp_el, ET.QName(namespace, "ProcessDocumentResult")
        )

        # Document element (optional) - as base64-encoded string
        doc_el = ET.SubElement(result_wrapper, ET.QName(namespace, "Document"))
        if resp_obj.document is not None:
            if isinstance(resp_obj.document, str):
                doc_el.text = resp_obj.document
            elif isinstance(resp_obj.document, bytes):
                # If bytes, decode to ASCII string (base64 is ASCII-safe)
                doc_el.text = resp_obj.document.decode("ascii")
            else:
                doc_el.text = str(resp_obj.document)

        # Error element (optional)
        err_el = ET.SubElement(result_wrapper, ET.QName(namespace, "Error"))
        if resp_obj.error is not None:
            err_el.text = str(resp_obj.error)

        envelope_bytes = build_soap_envelope(resp_el)

        logger.info(
            f"Sending SOAP response with document length: {len(resp_obj.document) if resp_obj.document else 0}"
        )

        return Response(
            content=envelope_bytes,
            media_type="text/xml; charset=utf-8",
            status_code=200,
        )

    return router
