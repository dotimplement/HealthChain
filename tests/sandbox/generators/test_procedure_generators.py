from healthchain.sandbox.generators.proceduregenerators import ProcedureGenerator
from healthchain.sandbox.generators.value_sets.procedurecodes import (
    ProcedureCodeSimple,
    ProcedureCodeComplex,
)


def test_ProcedureGenerator():
    value_set = [x.code for x in ProcedureCodeSimple().value_set]
    value_set.extend([x.code for x in ProcedureCodeComplex().value_set])
    procedure = ProcedureGenerator.generate(
        subject_reference="Patient/123", encounter_reference="Encounter/123"
    )
    assert procedure.subject.reference == "Patient/123"
    assert procedure.encounter.reference == "Encounter/123"
    assert procedure.code.coding[0].code in value_set
