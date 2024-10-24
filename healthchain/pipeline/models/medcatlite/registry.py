from spacy import registry
from typing import Dict, Optional

from healthchain.pipeline.models.medcatlite.utils import CDB, CuiFilter, Vocab, Config


# TODO pass in config on its own (not using the cdb one)
@registry.misc("medcatlite.token_processor_resources")
def create_token_processor_resources(cdb: CDB, config: Config) -> Dict:
    """Get preprocessor-specific resources"""
    return {"config": config, "cdb": cdb}


@registry.misc("medcatlite.ner_resources")
def create_ner_resources(cdb: CDB, config: Config) -> Dict:
    """Get NER-specific resources"""
    return {
        "config": config,
        "cdb": cdb,
    }


@registry.misc("medcatlite.linker_resources")
def create_linker_resources(
    cdb: CDB,
    config: Config,
    vocab: Optional[Vocab] = None,
    cui_filter: Optional[CuiFilter] = None,
) -> Dict:
    """Get linker-specific resources"""
    return {
        "config": config,
        "cdb": cdb,
        "vocab": vocab,
        "cui_filter": cui_filter,
    }
