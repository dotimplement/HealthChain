# generators.py

import random
import string

from faker import Faker
from healthchain.fhir_resources.primitives import (
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
from healthchain.fhir_resources.generalpurpose import (
    CodeableConcept,
    Coding,
)


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
        return self.registry.get(name)()


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
class BooleanGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return booleanModel(random.choice(["true", "false"]))


@register_generator
class CanonicalGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return canonicalModel(f"https://example/{faker.uri_path()}")


@register_generator
class CodeGenerator(BaseGenerator):
    # TODO: Codes can technically have whitespace but here I've left it out for simplicity
    @staticmethod
    def generate():
        return codeModel(
            "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        )


@register_generator
class DateGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return dateModel(faker.date())


@register_generator
class DateTimeGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return dateTimeModel(faker.date_time().isoformat())


@register_generator
class DecimalGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return decimalModel(faker.random_number())


@register_generator
class IdGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return idModel(faker.uuid4())


@register_generator
class InstantGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return instantModel(faker.date_time().isoformat())


@register_generator
class IntegerGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return integerModel(faker.random_int())


@register_generator
class MarkdownGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return markdownModel(faker.text())


@register_generator
class PositiveIntGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return positiveIntModel(faker.random_int(min=1))


@register_generator
class StringGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return stringModel(faker.word())


@register_generator
class TimeGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return timeModel(faker.time())


@register_generator
class UnsignedIntGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return unsignedIntModel(faker.random_int(min=0))


@register_generator
class UriGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return uriModel(f"https://example/{faker.uri_path()}")


@register_generator
class UrlGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return urlModel(f"https://example/{faker.uri_path()}")


@register_generator
class UuidGenerator(BaseGenerator):
    @staticmethod
    def generate():
        return uuidModel(faker.uuid4())


class CodeableConceptGenerator(BaseGenerator):
    @staticmethod
    def generate_from_valueset(ValueSet):
        value_set_instance = ValueSet()
        return CodeableConcept(
            coding=[
                Coding(
                    system=value_set_instance.system,
                    code=faker.random_element(value_set_instance.value_set)["code"],
                    display=faker.random_element(value_set_instance.value_set)[
                        "display"
                    ],
                    # extension=[ExtensionModel(value_set_instance.extension)],
                )
            ]
        )

    @staticmethod
    def generate():
        pass
