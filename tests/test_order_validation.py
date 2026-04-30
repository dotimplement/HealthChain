import pytest
from healthchain.models.hooks.ordersign import OrderSignContext
from healthchain.models.hooks.orderselect import OrderSelectContext


def test_ordersign_empty_draftorders():
    with pytest.raises(ValueError):
        OrderSignContext(
            userId="Practitioner/123",
            patientId="Patient/456",
            draftOrders={}
        )


def test_orderselect_invalid_selection():
    with pytest.raises(ValueError):
        OrderSelectContext(
            userId="Practitioner/123",
            patientId="Patient/456",
            selections=["invalidformat"]
        )