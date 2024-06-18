from pydantic import BaseModel

from typing import Dict


class CdaData(BaseModel):
    problems: Dict
    allergies: Dict
    medications: Dict
    note: str
