from pydantic import BaseModel


class NoteReaderRequest(BaseModel):
    document: str
