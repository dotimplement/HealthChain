from pydantic import BaseModel


class CdaRequest(BaseModel):
    document: str
