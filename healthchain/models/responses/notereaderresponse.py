from pydantic import BaseModel
from typing import Optional


class NoteReaderResponse(BaseModel):
    document: str
    error: Optional[str]
