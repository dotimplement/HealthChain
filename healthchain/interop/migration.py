from typing import Dict, List
from pathlib import Path
from healthchain.cda_parser.cdaannotator import CdaAnnotator
from healthchain.interop.engine import InteropEngine


class LegacyMigrator:
    """Helper class to migrate from legacy CdaAnnotator to new InteropEngine"""

    def __init__(self, config_dir: Path):
        self.engine = InteropEngine(config_dir)

    def migrate_document(self, cda_annotator: CdaAnnotator) -> List[Dict]:
        """Convert CdaAnnotator document to FHIR resources using new engine"""
        # Export CDA XML from annotator
        cda_xml = cda_annotator.export()

        # Use new engine to convert
        return self.engine.to_fhir(cda_xml, "CDA")
