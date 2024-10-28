from abc import ABC
from typing import List
from pydantic import BaseModel, ValidationError, field_validator
import json


class ValueSetEntry(BaseModel):
    code: str
    display: str

    @field_validator("code")
    def validate_code(cls, value):
        if not value.isdigit():
            raise ValueError("code must contain only digits")
        return value


class ValueSet(ABC):
    def __init__(self):
        self.value_set: List[ValueSetEntry] = []

    def add_code(self, code: str, display: str):
        try:
            entry = ValueSetEntry(code=code, display=display)
            self.value_set.append(entry)
        except ValidationError as e:
            print(f"Validation error: {e}")

    def load_from_json(self, file_path: str):
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
                for item in data:
                    self.add_code(item["code"], item["display"])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading JSON file: {e}")
