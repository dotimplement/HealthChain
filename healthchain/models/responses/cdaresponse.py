from pydantic import BaseModel
from typing import Optional


class CdaResponse(BaseModel):
    document: str
    error: Optional[str]
