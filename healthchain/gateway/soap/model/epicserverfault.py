from spyne import Unicode, Fault


class ServerFault(Fault):
    __namespace__ = "urn:epicsystems.com:Interconnect.2004-05.Faults"
    Type = Unicode
