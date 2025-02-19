from pydantic import BaseModel
from typing import Optional
from abc import ABC


class BaseHookContext(BaseModel, ABC):
    userId: str
    patientId: str
    encounterId: Optional[str] = None
