from healthchain.fhir_resources.bundle_resources import Bundle_EntryModel, BundleModel
from healthchain.data_generator.patient_generator import PatientGenerator
from healthchain.data_generator.encounter_generator import EncounterGenerator


def test_bundle_entry_model():
    patient_generator = PatientGenerator()
    patient = patient_generator.generate()
    encounter_generator = EncounterGenerator()
    encounter = encounter_generator.generate(patient_reference="Patient/123")

    # check that bundle can be created with out error

    bundle_patient_entry = Bundle_EntryModel(resource=patient)
    bundle_encounter_entry = Bundle_EntryModel(resource=encounter)
    bundle = BundleModel(entry=[bundle_patient_entry, bundle_encounter_entry])
    assert bundle.entry_field[0].resource_field == patient
    assert bundle.entry_field[1].resource_field == encounter
