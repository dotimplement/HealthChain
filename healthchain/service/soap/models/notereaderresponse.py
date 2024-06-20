from spyne import ComplexModel
from spyne import Unicode, ByteArray


class NoteReaderResponse(ComplexModel):
    __namespace__ = "urn:epic-com:Common.2013.Services"
    Document = ByteArray
    Error = Unicode
