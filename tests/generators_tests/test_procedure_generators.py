from healthchain.data_generators.proceduregenerators import ProcedureGenerator
from healthchain.data_generators.value_sets.procedurecodes import (
    ProcedureCodeSimple,
    ProcedureCodeComplex,
)


def test_ProcedureGenerator():
    value_set = [x.code for x in ProcedureCodeSimple().value_set]
    value_set.extend([x.code for x in ProcedureCodeComplex().value_set])
    procedure = ProcedureGenerator.generate(
        subject_reference="Patient/123", encounter_reference="Encounter/123"
    )
    assert procedure.resourceType == "Procedure"
    assert procedure.subject_field.reference_field == "Patient/123"
    assert procedure.encounter_field.reference_field == "Encounter/123"
    assert procedure.code_field.coding_field[0].code_field in value_set
