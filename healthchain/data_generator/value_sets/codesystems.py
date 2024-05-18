from enum import Enum


class CodeSystem(Enum):
    snomedct = "http://snomed.info/sct"
    loinc = "http://loinc.org"


class Extension(Enum):
    uk = "uk"
    international = "int"
