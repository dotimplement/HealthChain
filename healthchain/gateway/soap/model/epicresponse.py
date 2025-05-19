from spyne import ComplexModel
from spyne import Unicode, ByteArray


class Response(ComplexModel):
    __namespace__ = "urn:epic-com:Common.2013.Services"
    Document = ByteArray
    Error = Unicode
