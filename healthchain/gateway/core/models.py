from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Dict, Optional, List, Any


class EHREventType(str, Enum):
    PATIENT_ADMISSION = "patient.admission"
    PATIENT_DISCHARGE = "patient.discharge"
    MEDICATION_ORDER = "medication.order"
    LAB_RESULT = "lab.result"
    APPOINTMENT_SCHEDULE = "appointment.schedule"


class EHREvent(BaseModel):
    """Enhanced EHR event with validation"""

    event_type: EHREventType
    source_system: str
    timestamp: datetime
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SOAPEvent(EHREvent):
    """Special event type for SOAP messages"""

    raw_xml: str


class RequestModel(BaseModel):
    """Generic request model"""

    resource_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ResponseModel(BaseModel):
    """Generic response model with error handling"""

    status: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
