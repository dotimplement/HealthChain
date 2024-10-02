from healthchain.fhir_resources.bundleresources import BundleEntry, Bundle
from healthchain.fhir_resources.patient import Patient
from healthchain.fhir_resources.encounter import Encounter


def test_bundle_entry_model():
    patient = Patient()
    encounter = Encounter()

    bundle_patient_entry = BundleEntry(resource=patient)
    bundle_encounter_entry = BundleEntry(resource=encounter)
    bundle = Bundle(entry=[bundle_patient_entry, bundle_encounter_entry])
    assert bundle.entry_field[0].resource_field == patient
    assert bundle.entry_field[1].resource_field == encounter
