import base64
import xmltodict
import logging

from pydantic import BaseModel
from typing import Optional, Dict

from healthchain.utils.utils import search_key


log = logging.getLogger(__name__)


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
        xml_dict = xmltodict.parse(self.document)
        document = search_key(xml_dict, "tns:Document")
        if document is None:
            log.warning("Coudln't find document under namespace 'tns:Document")
            return ""

        cda = base64.b64decode(document).decode("UTF-8")

        return cda
