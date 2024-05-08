from healthchain.data_generator.base_generators import BaseGenerator, generator_registry, register_generator
from healthchain.data_generator.patient_generator import PeriodGenerator, ContactPointGenerator, AddressGenerator
from healthchain.fhir_resources.base_resources import PeriodModel, booleanModel, CodeableConceptModel, stringModel, CodingModel, uriModel, codeModel, dateTimeModel, positiveIntModel
from healthchain.fhir_resources.patient_resources import PatientModel, HumanNameModel, ContactPointModel, AddressModel
from healthchain.fhir_resources.practitioner_resources import PractitionerModel, Practitioner_QualificationModel, Practitioner_CommunicationModel
from faker import Faker


import random

faker = Faker()

@register_generator
class Practitioner_QualificationGenerator(BaseGenerator):
    qualification_value_set = [
    "PN", "AAS", "AA", "ABA", "AE", "AS", "BA", "BBA", "BE", "BFA", "BN", "BS",
    "BSL", "BSN", "BT", "CER", "CANP", "CMA", "CNP", "CNM", "CRN", "CNS", "CPNP",
    "CTR", "DIP", "DBA", "DED", "PharmD", "PHE", "PHD", "PHS", "MD", "DO", "EMT",
    "EMTP", "FPNP", "HS", "JD", "MA", "MBA", "MCE", "MDI", "MED", "MEE", "ME",
    "MFA", "MME", "MS", "MSL", "MSN", "MTH", "MDA", "MT", "NG", "NP", "PA", "RMA",
    "RN", "RPH", "SEC", "TS"]


    @staticmethod
    def generate():
        return Practitioner_QualificationModel(
            id=stringModel(string=faker.uuid4()),
            identifier=[generator_registry.get('IdentifierGenerator').generate()],
            code=codeModel(code=faker.random_element(elements=Practitioner_QualificationGenerator.qualification_value_set)),
            # TODO: Modify period generator to have flexibility to set to present date
            period=generator_registry.get('PeriodGenerator').generate(),
            # issuer=generator_registry.get('ReferenceGenerator').generate(),
        )
    

@register_generator
class PractitionerGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return PractitionerModel(
            id=stringModel(string=faker.uuid4()),
            identifier=[generator_registry.get('IdentifierGenerator').generate()],
            active=booleanModel(boolean=random.choice(['true', 'false'])),
            name=[generator_registry.get('HumanNameGenerator').generate()],
            telecom=[generator_registry.get('ContactPointGenerator').generate()],
            gender=codeModel(code=faker.random_element(elements=('male', 'female', 'other', 'unknown'))),
            address=[generator_registry.get('AddressGenerator').generate()],
            qualification=[generator_registry.get('Practitioner_QualificationGenerator').generate()],
            communication=[generator_registry.get('Practitioner_CommunicationGenerator').generate()],

        )