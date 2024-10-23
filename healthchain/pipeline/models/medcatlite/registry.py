from spacy import registry
from typing import Dict, Optional

from healthchain.pipeline.models.medcatlite.utils import CDB, Vocab


# TODO pass in config on its own (not using the cdb one)
@registry.misc("medcatlite.token_processor_resources")
def create_token_processor_resources(cdb: CDB) -> Dict:
    """Get preprocessor-specific resources"""
    return {"config": cdb.config.model_dump(), "cdb_word_freq": cdb.vocab}


@registry.misc("medcatlite.ner_resources")
def create_ner_resources(cdb: CDB) -> Dict:
    """Get NER-specific resources"""
    return {
        "config": cdb.config.model_dump(),
        "name2cuis": cdb.name2cuis,
        "snames": cdb.snames,
    }


@registry.misc("medcatlite.linker_resources")
def create_linker_resources(cdb: CDB, vocab: Optional[Vocab] = None) -> Dict:
    """Get linker-specific resources"""
    return {
        "name2cui2status": cdb.name2cuis2status,
        "cui2average_confidence": cdb.cui2average_confidence,
        "cui2names": cdb.cui2names,
        "weighted_average_function": cdb.weighted_average_function,
        "vocab": vocab,  # Pass the MedCAT vocab
    }
