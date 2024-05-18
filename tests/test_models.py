from healthchain.models.hooks.encounterdischarge import EncounterDischargeContext
from healthchain.models.hooks.patientview import PatientViewContext
from healthchain.models.hooks.orderselect import OrderSelectContext
from healthchain.models.hooks.ordersign import OrderSignContext


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
