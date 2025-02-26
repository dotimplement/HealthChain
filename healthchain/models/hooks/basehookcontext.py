from pydantic import BaseModel
from abc import ABC


class BaseHookContext(BaseModel, ABC):
    userId: str
    patientId: str
