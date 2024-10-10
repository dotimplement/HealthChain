import logging
from healthchain.io.containers import DataContainer
from healthchain.io.baseconnector import Connector

log = logging.getLogger(__name__)


class CdsFhirConnector(Connector):
    """
    CdsFhirConnector class for handling FHIR (Fast Healthcare Interoperability Resources) documents
    for CDS Hooks.
    """

    def __init__(self):
        pass

    def input(self, data) -> DataContainer:
        pass

    def output(self, result: DataContainer):
        pass
