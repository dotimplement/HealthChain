from enum import Enum


class SimpleCodeSystem(Enum):
    snomedct = "http://snomed.info/sct"
    loinc = "http://loinc.org"


class CodeExtension(Enum):
    uk = "uk"
    international = "int"
