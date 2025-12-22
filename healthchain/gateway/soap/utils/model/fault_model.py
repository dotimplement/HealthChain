from dataclasses import dataclass
from typing import Optional

SOAP_FAULT_NS = "http://schemas.xmlsoap.org/soap/envelope/"
CUSTOM_FAULT_NS = "urn:epicsystems.com:Interconnect.2004-05.Faults"
RESPONSE_NS = "urn:epic-com:Common.2013.Services"


@dataclass
class ServerFault(Exception):
    message: str
    type: Optional[str] = None
    code: str = "Server"

    def to_xml(self) -> str:
        """
        Create a SOAP Fault XML block representing this error.
        """
        return f"""
<soap:Fault xmlns:soap="{SOAP_FAULT_NS}">
  <faultcode>soap:{self.code}</faultcode>
  <faultstring>{self.message}</faultstring>
  <detail>
    <Error xmlns="{CUSTOM_FAULT_NS}">
      <Type>{self.type or ""}</Type>
    </Error>
  </detail>
</soap:Fault>
""".strip()


@dataclass
class ClientFault(Exception):
    message: str
    code: str = "Client"

    def to_xml(self) -> str:
        return f"""
<soap:Fault xmlns:soap="{SOAP_FAULT_NS}">
  <faultcode>soap:{self.code}</faultcode>
  <faultstring>{self.message}</faultstring>
</soap:Fault>
""".strip()


@dataclass
class Response:
    """
    Replacement for Spyne ComplexModel Response.

    Fields:
        Document: bytes
        Error: Optional[str]
    """

    Document: bytes
    Error: Optional[str] = None

    def to_xml(self) -> str:
        """
        Create the SOAP XML body for a successful response.
        Mirrors Spyne's output shape.
        """

        # Escape XML content (very important)
        from xml.sax.saxutils import escape

        doc_value = escape(self.Document.decode("utf-8")) if self.Document else ""
        error_value = escape(self.Error) if self.Error else ""

        return f"""
<Response xmlns="{RESPONSE_NS}">
  <Document>{doc_value}</Document>
  <Error>{error_value}</Error>
</Response>
""".strip()
