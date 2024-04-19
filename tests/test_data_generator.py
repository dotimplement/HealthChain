import pytest
from healthchain.doppeldata import data_generator as dg

# Define your test functions here
def test_doppeldata_integrate():
    data = dg.generate_data()
    assert isinstance(data, dict)




# Run the tests
if __name__ == "__main__":
    pytest.main()
