from enum import Enum


class ApiProtocol(Enum):
    """
    Enum defining the supported API protocols.

    Available protocols:
    - soap: SOAP protocol
    - rest: REST protocol
    """

    soap = "SOAP"
    rest = "REST"
