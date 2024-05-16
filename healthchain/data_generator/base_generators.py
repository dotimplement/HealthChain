# generators.py

import random
import string

from healthchain.fhir_resources.primitive_resources import (
    booleanModel,
    canonicalModel,
    codeModel,
    dateModel,
    dateTimeModel,
    decimalModel,
    idModel,
    instantModel,
    integerModel,
    markdownModel,
    positiveIntModel,
    stringModel,
    timeModel,
    unsignedIntModel,
    uriModel,
    urlModel,
    uuidModel,
)

from faker import Faker

faker = Faker()


class Registry:
    def __init__(self):
        self.registry = {}

    def register(self, cls):
        self.registry[cls.__name__] = cls
        return cls

    def get(self, name):
        if name not in self.registry:
            raise ValueError(f"No generator registered for '{name}'")
        return self.registry.get(name)


generator_registry = Registry()


def register_generator(cls):
    generator_registry.register(cls)
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
        return booleanModel(random.choice(["true", "false"]))


@register_generator
class canonicalGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return canonicalModel(f"https://example/{faker.uri_path()}")


@register_generator
class codeGenerator(BaseGenerator):
    # TODO: Codes can technically have whitespace but here I've left it out for simplicity
    @staticmethod
    def generate():
        return codeModel(
            "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        )


@register_generator
class dateGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return dateModel(faker.date())


@register_generator
class dateTimeGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return dateTimeModel(faker.date_time().isoformat())


@register_generator
class decimalGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return decimalModel(faker.random_number())


@register_generator
class idGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return idModel(faker.uuid4())


@register_generator
class instantGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return instantModel(faker.date_time().isoformat())


@register_generator
class integerGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return integerModel(faker.random_int())


@register_generator
class markdownGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return markdownModel(faker.text())


@register_generator
class positiveIntGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return positiveIntModel(faker.random_int(min=1))


@register_generator
class stringGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return stringModel(faker.word())


@register_generator
class timeGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return timeModel(faker.time())


@register_generator
class unsignedIntGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return unsignedIntModel(faker.random_int(min=0))


@register_generator
class uriGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return uriModel(f"https://example/{faker.uri_path()}")


@register_generator
class urlGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return urlModel(f"https://example/{faker.uri_path()}")


@register_generator
class uuidGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return uuidModel(faker.uuid4())
