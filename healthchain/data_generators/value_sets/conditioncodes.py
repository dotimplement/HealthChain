from dataclasses import dataclass, field
from typing import List, Dict

from .base import ValueSet
from .codesystems import SimpleCodeSystem, CodeExtension


# Format: ResourceFieldParam
@dataclass
class ConditionCodeSimple(ValueSet):
    system: SimpleCodeSystem = SimpleCodeSystem.snomedct
    extension: CodeExtension = CodeExtension.uk
    value_set: List[Dict] = field(
        default_factory=lambda: [
            {"code": "57054005", "display": "Acute myocardial infarction"},
            {"code": "233604007", "display": "Pneumonia"},
            {"code": "42343007", "display": "Congestive heart failure"},
            {
                "code": "195951007",
                "display": "Chronic obstructive pulmonary disease exacerbation",
            },
            {"code": "14669001", "display": "Acute renal failure"},
            {"code": "91302008", "display": "Sepsis"},
            {"code": "230690007", "display": "Stroke"},
            {"code": "128053003", "display": "Deep vein thrombosis"},
            {"code": "59282003", "display": "Pulmonary embolism"},
            {"code": "67782005", "display": "Acute respiratory distress syndrome"},
            {"code": "74400008", "display": "Appendicitis"},
            {"code": "420422005", "display": "Diabetic ketoacidosis"},
            {"code": "74474003", "display": "Gastrointestinal bleed"},
            {"code": "125605004", "display": "Fracture of bone"},
            {"code": "128045006", "display": "Cellulitis"},
            {"code": "68566005", "display": "Urinary tract infection"},
            {"code": "75694006", "display": "Pancreatitis"},
            {"code": "19943007", "display": "Cirrhosis of liver"},
            {"code": "49436004", "display": "Atrial fibrillation"},
            {"code": "271737000", "display": "Anemia"},
            {"code": "13200003", "display": "Peptic ulcer disease"},
            {"code": "363346000", "display": "Cancer"},
            {"code": "706882009", "display": "Hypertensive crisis"},
            {"code": "7180009", "display": "Meningitis"},
            {
                "code": "762489000",
                "display": "Acute complication due to diabetes mellitus",
            },
            {"code": "398254007", "display": "Pre-eclampsia"},
        ]
    )


@dataclass
class ConditionCodeComplex(ValueSet):
    system: SimpleCodeSystem = SimpleCodeSystem.snomedct
    extension: CodeExtension = CodeExtension.uk
    value_set: List[Dict] = field(
        default_factory=lambda: [
            {"code": "46701001", "display": "Acute myocarditis"},
            {
                "code": "429257001",
                "display": "Disorder of transplanted heart",
            },
            {"code": "17602002", "display": "Amyloidosis"},
            {"code": "213320003", "display": "Anaphylactic shock caused by serum"},
            {"code": "67362008", "display": "Aortic aneurysm"},
            {
                "code": "428668000",
                "display": "Apraxia due to cerebrovascular accident",
            },
            {
                "code": "448418006",
                "display": "Sepsis caused by Streptococcus",
            },
            {"code": "45816000", "display": "Pyelonephritis"},
            {
                "code": "385093006",
                "display": "Community acquired pneumonia",
            },
            {
                "code": "1010616001",
                "display": "Cirrhosis of liver due to classical cystic fibrosis",
            },
            {"code": "46177005", "display": "End-stage renal disease"},
            {"code": "90935002", "display": "Hemophilia"},
            {"code": "118601006", "display": "Non-Hodgkin's lymphoma"},
            {
                "code": "700250006",
                "display": "Idiopathic pulmonary fibrosis",
            },
            {"code": "93143009", "display": "Leukemia"},
            {"code": "200936003", "display": "Lupus erythematosus"},
            {"code": "70272006", "display": "Malignant hypertension"},
            {"code": "24700007", "display": "Multiple sclerosis"},
            {"code": "78314001", "display": "Osteogenesis imperfecta"},
            {"code": "363418001", "display": "Pancreatic cancer"},
            {"code": "49049000", "display": "Parkinson's disease"},
            {"code": "70995007", "display": "Pulmonary hypertension"},
            {"code": "89155008", "display": "Systemic sclerosis"},
            {"code": "56819008", "display": "Endocarditis"},
            {"code": "201727001", "display": "Arthropathy in ulcerative colitis"},
        ]
    )


# don't use
@dataclass
class ConditionCodeProblemListSimple(ValueSet):
    system: SimpleCodeSystem = SimpleCodeSystem.snomedct
    extension: CodeExtension = CodeExtension.uk
    value_set: List[Dict] = field(
        default_factory=lambda: [
            {"code": "73211009", "display": "Diabetes mellitus"},
            {"code": "38341003", "display": "Hypertension"},
            {"code": "56265001", "display": "Heart disease"},
            {"code": "195967001", "display": "Asthma"},
            {"code": "709044004", "display": "Chronic kidney disease"},
            {"code": "396275006", "display": "Osteoarthritis"},
            {"code": "64859006", "display": "Osteoporosis"},
            {"code": "26929004", "display": "Alzheimer's disease"},
            {"code": "84757009", "display": "Epilepsy"},
            {"code": "267874003", "display": "Scleroderma"},
            {"code": "49049000", "display": "Parkinson's disease"},
            {"code": "23986001", "display": "Glaucoma"},
            {"code": "69896004", "display": "Rheumatoid arthritis"},
            {"code": "197480006", "display": "Anxiety disorder"},
            {"code": "35489007", "display": "Depressive disorder"},
            {
                "code": "13645005",
                "display": "Chronic obstructive pulmonary disease",
            },
            {"code": "328383001", "display": "Chronic liver disease"},
            {"code": "9014002", "display": "Psoriasis"},
            {"code": "40055000", "display": "Chronic sinusitis"},
            {"code": "34000006", "display": "Crohn's disease"},
            {"code": "24700007", "display": "Multiple sclerosis"},
            {
                "code": "840580004",
                "display": "Peripheral arterial disease",
            },
            {"code": "45053005", "display": "Chronic thyroiditis"},
            {"code": "737305006", "display": "Chronic pain"},
            {"code": "64766004", "display": "Ulcerative colitis"},
        ],
    )
