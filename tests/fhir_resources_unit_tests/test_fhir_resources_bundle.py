from healthchain.fhir_resources.bundleresources import BundleEntry, Bundle
from healthchain.data_generators import PatientGenerator, EncounterGenerator


def test_bundle_entry_model():
    patient_generator = PatientGenerator()
    patient = patient_generator.generate()
    encounter_generator = EncounterGenerator()
    encounter = encounter_generator.generate()

    bundle_patient_entry = BundleEntry(resource=patient)
    bundle_encounter_entry = BundleEntry(resource=encounter)
    bundle = Bundle(entry=[bundle_patient_entry, bundle_encounter_entry])
    assert bundle.entry_field[0].resource_field == patient
    assert bundle.entry_field[1].resource_field == encounter
