# Based on/Adapted from MedCAT
# Original repository: https://github.com/cogstack/medcat
# Copyright 2024 CogStack
# Licensed under the Elastic License 2.0


from spacy.language import Language
from spacy.tokens import Doc, Span
from typing import Optional, List, Tuple
from healthchain.pipeline.models.medcatlite.medcatutils import (
    CDB,
    ContextModel,
    Vocab,
    LabelStyle,
)


@Language.factory("medcat_linker")
class Linker:
    def __init__(self, nlp: Language, name: str, cdb: CDB, vocab: Vocab, config: dict):
        self.name = name
        self.cdb = cdb
        self.vocab = vocab
        self.config = config
        self.context_model = ContextModel(self.cdb, self.vocab, self.config)
        # self.train_counter = {}

        if not Doc.has_extension("ents"):
            Doc.set_extension("ents", default=[])
        if not Span.has_extension("detected_name"):
            Span.set_extension("detected_name", default=None)
        if not Span.has_extension("link_candidates"):
            Span.set_extension("link_candidates", default=[])
        if not Span.has_extension("cui"):
            Span.set_extension("cui", default=None)
        if not Span.has_extension("context_similarity"):
            Span.set_extension("context_similarity", default=None)

    def __call__(self, doc: Doc) -> Doc:
        doc.ents = []
        linked_entities = []

        self._inference_mode(doc, linked_entities)

        doc._.ents = linked_entities
        self._create_main_ann(doc)

        if self.config["general"]["make_pretty_labels"] is not None:
            self._make_pretty_labels(
                doc, LabelStyle[self.config["general"]["make_pretty_labels"]]
            )

        if self.config["general"][
            "map_cui_to_group"
        ] is not None and self.cdb.addl_info.get("cui2group", {}):
            self._map_ents_to_groups(doc)

        return doc

    def _inference_mode(self, doc: Doc, linked_entities: List[Span]):
        for entity in doc._.ents:
            if entity._.link_candidates is not None:
                cui, context_similarity = self._process_entity(entity, doc)
                if (
                    cui
                    and self._check_filters(cui)
                    and self._check_similarity_threshold(cui, context_similarity)
                ):
                    entity._.cui = cui
                    entity._.context_similarity = context_similarity
                    linked_entities.append(entity)

    def _process_entity(self, entity: Span, doc: Doc) -> Tuple[Optional[str], float]:
        if entity._.detected_name is not None:
            name = entity._.detected_name
            cuis = entity._.link_candidates
            if len(cuis) > 0:
                if self._should_disambiguate(name, cuis):
                    return self.context_model.disambiguate(cuis, entity, name, doc)
                cui = cuis[0]
                if self.config["linking"]["always_calculate_similarity"]:
                    context_similarity = self.context_model.similarity(cui, entity, doc)
                else:  # inserted
                    context_similarity = 1
                return (cui, context_similarity)
        else:  # inserted
            return self.context_model.disambiguate(
                entity._.link_candidates, entity, "unk-unk", doc
            )
        return (None, 0)

    def _should_disambiguate(self, name: str, cuis: List[str]) -> bool:
        cnf_l = self.config["linking"]
        if len(name) < cnf_l["disamb_length_limit"]:
            return True
        if len(cuis) == 1 and self.cdb.name2cuis2status[name][cuis[0]] in {"PD", "N"}:
            return True
        if len(cuis) > 1:
            return True
        return False

    def _check_filters(self, cui: str) -> bool:
        return self.config["linking"]["filters"].check_filters(cui)

    def _check_similarity_threshold(self, cui: str, context_similarity: float) -> bool:
        th_type = self.config["linking"]["similarity_threshold_type"]
        threshold = self.config["linking"]["similarity_threshold"]
        if th_type == "static":
            return context_similarity >= threshold
        if th_type == "dynamic":
            return (
                context_similarity >= self.cdb.cui2average_confidence[cui] * threshold
            )
        return False

    def _create_main_ann(self, doc: Doc):
        return

    def _make_pretty_labels(self, doc: Doc, style: LabelStyle):
        return

    def _map_ents_to_groups(self, doc: Doc):
        return
