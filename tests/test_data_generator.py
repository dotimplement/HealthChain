import pytest
from healthchain.doppeldata import data_generator as dg

# Define your test functions here
def test_doppeldata_integrate():
    data = dg.generate_data()
    assert isinstance(data, dict)



# The data generator and the data model are tightly coupled.
# We need to write a test that will fail if one is changed and the other is not.


# Run the tests
if __name__ == "__main__":
    pytest.main()
