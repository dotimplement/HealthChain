from healthchain.models.hooks import (
    EncounterDischargeContext,
    PatientViewContext,
    OrderSelectContext,
    OrderSignContext,
)


def test_default_id_generator():
    encounter_discharge = EncounterDischargeContext()
    patient_view = PatientViewContext()
    order_select = OrderSelectContext(
        selections=["Example/123"], draftOrders={"name": "example", "id": "123"}
    )
    order_sign = OrderSignContext(draftOrders={"name": "example", "id": "123"})

    assert encounter_discharge
    assert patient_view
    assert order_select
    assert order_sign
