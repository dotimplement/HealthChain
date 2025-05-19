from spyne import Unicode, Fault


class ClientFault(Fault):
    __namespace__ = "urn:epicsystems.com:Interconnect.2004-05.Faults"
    Type = Unicode
