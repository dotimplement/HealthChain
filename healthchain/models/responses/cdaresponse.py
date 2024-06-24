import base64
import xmltodict

from pydantic import BaseModel
from typing import Optional, Dict

from healthchain.cda_parser.cdaparser import search_key_from_xml_string


class CdaResponse(BaseModel):
    document: str
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict):
        """
        Loads data from dict (xmltodict format)
        """
        return cls(document=xmltodict.unparse(data))

    def model_dump(self, *args, **kwargs) -> Dict:
        """
        Dumps document as dict with xmltodict
        """
        return xmltodict.parse(self.document)

    def model_dump_xml(self, *args, **kwargs) -> str:
        """
        Decodes and dumps document as an xml string
        """
        document = search_key_from_xml_string(self.document, "tns:Document")
        cda = base64.b64decode(document).decode("UTF-8")

        return cda
