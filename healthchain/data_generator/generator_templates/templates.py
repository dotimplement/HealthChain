from pydantic import BaseModel


class patient_template_1(BaseModel):
    name: list = [{"family": "Doe", "given": ["John"], "prefix": ["Mr."]}]
    birthDate: str = "1999-01-01"
