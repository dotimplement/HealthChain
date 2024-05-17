from healthchain.data_generator.procedure_generators import ProcedureModelGenerator


def test_procedure_model_generator():
    procedure = ProcedureModelGenerator.generate(
        subject_reference="Patient/123", encounter_reference="Encounter/123"
    )
    assert procedure.resourceType == "Procedure"
    assert procedure.subject_field.reference_field == "Patient/123"
    assert procedure.encounter_field.reference_field == "Encounter/123"
    # assert procedure.status_field.coding_field[0].code_field in ["in-progress", "completed"]
    assert procedure.code_field.coding_field[0].code_field in ["123456", "654321"]
