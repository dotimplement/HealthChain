from dataclasses import dataclass, field
from typing import List, Dict

from .base import ValueSet
from .codesystems import SimpleCodeSystem, CodeExtension


# Format: ResourceFieldParam
@dataclass
class ProcedureCodeSimple(ValueSet):
    system: SimpleCodeSystem = SimpleCodeSystem.snomedct
    extension: CodeExtension = CodeExtension.uk
    value_set: List[Dict] = field(
        default_factory=lambda: [
            {"code": "232717009", "display": "Coronary artery bypass graft"},
            {"code": "52734007", "display": "Total hip replacement"},
            {"code": "609588000", "display": "Total knee replacement"},
            {"code": "236886002", "display": "Hysterectomy"},
            {"code": "34068001", "display": "Heart valve replacement"},
            {"code": "70536003", "display": "Kidney transplantation"},
            {"code": "55705006", "display": "Spinal fusion"},
            {
                "code": "771453009",
                "display": "Repair of abdominal aortic aneurysm with insertion of stent",
            },
            {"code": "387731002", "display": "Laminectomy"},
            {"code": "1231734007", "display": "Mastectomy"},
            {"code": "173171007", "display": "Lobectomy of lung"},
            {"code": "80146002", "display": "Appendectomy"},
            {"code": "442338001", "display": "Gastric bypass"},
            {"code": "66951008", "display": "Carotid endarterectomy"},
            {"code": "44558001", "display": "Repair of inguinal hernia"},
            {"code": "90470006", "display": "Prostatectomy"},
            {"code": "16541006", "display": "Pancreatectomy"},
            {"code": "304384006", "display": "Complete repair of rotator cuff"},
            {"code": "38102005", "display": "Removal of gallbladder"},
            {"code": "13619001", "display": "Thyroidectomy"},
            {"code": "11466000", "display": "Cesarean section"},
            {"code": "18027006", "display": "Liver transplantation"},
            {"code": "307280005", "display": "Implantation of cardiac pacemaker"},
            {"code": "110473004", "display": "Cataract surgery"},
            {"code": "173422009", "display": "Tonsillectomy"},
        ]
    )


@dataclass
class ProcedureCodeComplex(ValueSet):
    system: SimpleCodeSystem = SimpleCodeSystem.snomedct
    extension: CodeExtension = CodeExtension.uk
    value_set: List[Dict] = field(
        default_factory=lambda: [
            {"code": "232723004", "display": "Coronary artery bypass grafts x 5"},
            {
                "code": "1231414005",
                "display": "Total replacement of hip joint using autogenous bone graft",
            },
            {
                "code": "1287945008",
                "display": "Prosthetic hybrid total knee replacement",
            },
            {
                "code": "1187630003",
                "display": "Subtotal hysterectomy via vaginal approach",
            },
            {
                "code": "30456009",
                "display": "Open heart valvuloplasty without replacement of valve",
            },
            {"code": "56994000", "display": "Dorsal spinal fusion for pseudoarthrosis"},
            {
                "code": "698996009",
                "display": "Elective repair of suprarenal abdominal aortic aneurysm",
            },
            {"code": "59620004", "display": "Mastectomy for gynecomastia"},
            {"code": "726428009", "display": "Lobectomy of upper lobe of right lung"},
            {
                "code": "708876004",
                "display": "Laparoscopic appendectomy using robotic assistance",
            },
            {
                "code": "30803004",
                "display": "Printen and Mason operation, high gastric bypass",
            },
            {
                "code": "276950008",
                "display": "Percutaneous endarterectomy of external carotid artery",
            },
            {
                "code": "736717003",
                "display": "Repair of recurrent left inguinal hernia",
            },
            {
                "code": "176262001",
                "display": "Radical prostatectomy with pelvic node sampling",
            },
            {"code": "61774002", "display": "Repair of rotator cuff by suture"},
            {
                "code": "174521005",
                "display": "Removal of foreign body from gallbladder ",
            },
            {
                "code": "237486002",
                "display": "Total thyroidectomy with cervical lymph node dissection",
            },
            {
                "code": "236986001",
                "display": "Emergency upper segment cesarean section",
            },
            {
                "code": "426356008",
                "display": "Orthotopic transplantation of whole liver",
            },
            {
                "code": "309405007",
                "display": "Implantation of simple one wire intravenous cardiac pacemaker",
            },
            {
                "code": "432768005",
                "display": "Repair of fracture of hip by nailing using fluoroscopic guidance",
            },
            {
                "code": "425825000",
                "display": "Plasma mediated ablation of bilateral tonsils",
            },
        ]
    )
