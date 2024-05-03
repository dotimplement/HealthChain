# generators.py

import random
import string

from healthchain.fhir_resources.base_resources import booleanModel, canonicalModel, codeModel, dateModel, dateTimeModel, decimalModel, idModel, instantModel, integerModel, markdownModel, positiveIntModel, stringModel, timeModel, unsignedIntModel, uriModel, urlModel, uuidModel

from faker import Faker
faker = Faker()

generator_registry = {}

def register_generator(cls):
    generator_registry[cls.__name__] = cls
    return cls

@register_generator
class BaseGenerator:
    @staticmethod
    def generate():
        raise NotImplementedError("Each generator must implement a 'generate' method.")

@register_generator
class booleanGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return booleanModel(boolean=random.choice(['true', 'false']))
    

@register_generator
class canonicalGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return canonicalModel(canonical=f"https://example/{faker.uri_path()}")
    

@register_generator
class codeGenerator(BaseGenerator):
    # TODO: Codes can technically have whitespace but here I've left it out for simplicity
    @staticmethod
    def generate():
        return codeModel(code=''.join(random.choices(string.ascii_uppercase + string.digits, k=6)))
    

@register_generator
class dateGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return dateModel(date=faker.date())
    

@register_generator
class dateTimeGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return dateTimeModel(dateTime=faker.date_time().isoformat())
    

@register_generator
class decimalGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return decimalModel(decimal=faker.random_number())
    

@register_generator
class idGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return idModel(id=faker.uuid4())
    

@register_generator
class instantGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return instantModel(instant=faker.date_time().isoformat())
    

@register_generator
class integerGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return integerModel(integer=faker.random_int())
    

@register_generator
class markdownGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return markdownModel(markdown=faker.text())
    

@register_generator
class positiveIntGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return positiveIntModel(positiveInt=faker.random_int(min=1))
    

@register_generator
class stringGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return stringModel(string=faker.word())
    

@register_generator
class timeGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return timeModel(time=faker.time())
    

@register_generator
class unsignedIntGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return unsignedIntModel(unsignedInt=faker.random_int(min=0))
    

@register_generator
class uriGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return uriModel(uri=f"https://example/{faker.uri_path()}")
    

@register_generator
class urlGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return urlModel(url=f"https://example/{faker.uri_path()}")
    

@register_generator
class uuidGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return uuidModel(uuid=faker.uuid4())