from dataclasses import dataclass, field
from typing import List, Dict

from .base import ValueSet
from .codesystems import SimpleCodeSystem, CodeExtension

# using virtual therapeutic moiety (medicinal product) snomed form as it's just for vibes


# Format: ResourceFieldParam
@dataclass
class MedicationRequestMedication(ValueSet):
    system: SimpleCodeSystem = SimpleCodeSystem.snomedct
    extension: CodeExtension = CodeExtension.uk
    value_set: List[Dict] = field(
        default_factory=lambda: [
            {"code": "774656009", "display": "Aspirin"},
            {"code": "773455007", "display": "Atorvastatin"},
            {"code": "776713006", "display": "Metformin"},
            {"code": "776550005", "display": "Lisinopril"},
            {"code": "776526008", "display": "Levothyroxine"},
            {"code": "774557006", "display": "Amlodipine"},
            {"code": "777537002", "display": "Simvastatin"},
            {"code": "777537002", "display": "Omeprazole"},
            {"code": "776577001", "display": "Losartan"},
            {"code": "777483005", "display": "Salbutamol"},
            {"code": "776060008", "display": "Gabapentin"},
            {"code": "776226009", "display": "Hydrochlorothiazide"},
            {"code": "776052007", "display": "Furosemide"},
            {"code": "776770001", "display": "Metoprolol"},
            {"code": "777059008", "display": "Pantoprazole"},
            {"code": "777310000", "display": "Prednisone"},
            {"code": "776824002", "display": "Montelukast"},
            {"code": "776016008", "display": "Fluticasone"},
            {"code": "774586009", "display": "Amoxicillin"},
            {"code": "777521008", "display": "Sertraline"},
            {"code": "777990007", "display": "Zolpidem"},
            {"code": "777816004", "display": "Tramadol"},
            {"code": "777947006", "display": "Warfarin"},
            {"code": "777027001", "display": "Oxycodone"},
            {"code": "777673003", "display": "Tamsulosin"},
        ]
    )
