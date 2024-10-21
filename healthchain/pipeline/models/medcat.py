import json
import os
import re
import logging
import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span, Token
from functools import lru_cache
from typing import Dict, Optional, List, Any, Tuple
from healthchain.pipeline.models.medcatutils import (
    CDB,
    Config,
    ContextModel,
    BasicSpellChecker,
    Vocab,
    LabelStyle,
    attempt_unpack,
)


logger = logging.getLogger(__name__)


@Language.factory("medcat_ner")
def create_ner(nlp: Language, name: str):
    return NER(nlp, name)


class NER:
    def __init__(self, nlp: Language, name: str, cdb: CDB, config: Config):
        self.nlp = nlp
        self.name = name
        self.cdb = cdb
        self.config = config

        if not Doc.has_extension("to_skip"):
            Doc.set_extension("to_skip", default=False)
        if not Token.has_extension("norm"):
            Token.set_extension("norm", default="")
        if not Span.has_extension("link_candidates"):
            Span.set_extension("link_candidates", default=[])

    def process_token(
        self, doc: Doc, tokens: List[spacy.tokens.Token], start_index: int
    ):
        current_tokens = [tokens[start_index]]
        name_versions = [tokens[start_index]._.norm, tokens[start_index].lower_]
        name = self.get_initial_name(name_versions)
        if name and name in self.cdb.name2cuis and (not tokens[start_index].is_stop):
            self.annotate_name(name, current_tokens, doc)
        if name:
            for j in range(start_index + 1, len(tokens)):
                if tokens[j].i - tokens[j - 1].i - 1 > self.config.ner.max_skip_tokens:
                    return
                current_tokens.append(tokens[j])
                name_versions = [tokens[j]._.norm, tokens[j].lower_]
                name_changed, name_reverse = self.update_name(name, name_versions)
                if name_changed:
                    if name in self.cdb.name2cuis:
                        self.annotate_name(name, current_tokens, doc)
                else:  # inserted
                    if name_reverse:
                        if name_reverse in self.cdb.name2cuis:
                            self.annotate_name(name_reverse, current_tokens, doc)
                    else:  # inserted
                        break

    def get_initial_name(self, name_versions: List[str]) -> str:
        for name_version in name_versions:
            if name_version in self.cdb.snames:
                return name_version
            if name_version in self.cdb.name2cuis:
                return name_version
        else:  # inserted
            return ""

    def update_name(
        self, name: str, name_versions: List[str]
    ) -> Tuple[bool, Optional[str]]:
        for name_version in name_versions:
            new_name = name + self.config.general.separator + name_version
            if new_name in self.cdb.snames:
                return (True, None)
            if self.config.ner.get("try_reverse_word_order", False):
                reverse_name = name_version + self.config.general.separator + name
                if reverse_name in self.cdb.snames:
                    return (False, reverse_name)
        else:  # inserted
            return (False, None)

    def annotate_name(self, name: str, tokens: List[spacy.tokens.Token], doc: Doc):
        start = tokens[0].i
        end = tokens[(-1)].i + 1
        # span = doc[start:end]
        if len(doc.ents) == 0 or not any(
            (e.start <= start < e.end or start <= e.start < end for e in doc.ents)
        ):
            ent = Span(doc, start, end, label="CUSTOM")
            doc.ents = list(doc.ents) + [ent]
            ent._.set("link_candidates", self.cdb.name2cuis.get(name, []))


@Language.factory("medcat_token_processor")
def create_token_processor(
    nlp: Language,
    name: str,
    config: Dict[str, Any],
    spell_checker: Optional[object] = None,
):
    return TokenProcessor(nlp, name, config, spell_checker)


class TokenProcessor:
    def __init__(
        self,
        nlp: Language,
        name: str,
        config: Dict[str, Any],
        spell_checker: Optional[object] = None,
    ):
        self.nlp = nlp
        self.config = config
        self.spell_checker = spell_checker
        self.CONTAINS_NUMBER = re.compile("\\d")
        self.punct_checker = config["preprocessing"]["punct_checker"]
        self.word_skipper = config["preprocessing"]["word_skipper"]
        self.lemmatizer = spacy.load(
            config["general"]["spacy_model"],
            disable=config["general"]["spacy_disabled_components"],
        )

        if not Token.has_extension("norm"):
            Token.set_extension("norm", default="")
        if not Token.has_extension("to_skip"):
            Token.set_extension("to_skip", default=False)
        if not Token.has_extension("is_punct"):
            Token.set_extension("is_punct", default=False)

    def __call__(self, doc: Doc) -> Doc:
        for token in doc:
            self.process_token(token)
        return doc

    def process_token(self, token: Token):
        self.tag_token(token)
        if not token._.to_skip:
            self.normalize_token(token)

    def tag_token(self, token: Token):
        cnf_p = self.config["preprocessing"]
        if (
            self.punct_checker.match(token.lower_)
            and token.text not in cnf_p["keep_punct"]
        ):
            token._.is_punct = True
            token._.to_skip = True
        else:  # inserted
            if self.word_skipper.match(token.lower_):
                token._.to_skip = True
            else:  # inserted
                if cnf_p["skip_stopwords"] and token.is_stop:
                    token._.to_skip = True

    def normalize_token(self, token: Token):
        if len(token.lower_) < self.config["preprocessing"]["min_len_normalize"]:
            token._.norm = token.lower_
        else:  # inserted
            if (
                self.config["preprocessing"]["do_not_normalize"]
                and token.tag_ is not None
                and (token.tag_ in self.config["preprocessing"]["do_not_normalize"])
            ):
                token._.norm = token.lower_
            else:  # inserted
                if token.lemma_ == "-PRON-":
                    token._.norm = token.lemma_
                    token._.to_skip = True
                else:  # inserted
                    token._.norm = token.lemma_.lower()
        if self.config["general"]["spell_check"]:
            self.apply_spell_check(token)

    def apply_spell_check(self, token: Token):
        if (
            len(token.text) >= self.config["general"]["spell_check_len_limit"]
            and (not token._.is_punct)
            and (token.lower_ not in self.spell_checker)
            and (not self.CONTAINS_NUMBER.search(token.lower_))
        ):
            fix = self.spell_checker.fix(token.lower_)
            if fix is not None:
                tmp = self.lemmatizer(fix)[0]
                if (
                    len(token.lower_)
                    < self.config["preprocessing"]["min_len_normalize"]
                ):
                    token._.norm = tmp.lower_
                else:  # inserted
                    token._.norm = tmp.lemma_.lower()


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


class MedCATLite:
    def __init__(
        self,
        cdb: Optional[CDB] = None,
        vocab: Optional[Vocab] = None,
        config: Optional[Config] = None,
    ):
        self.config = config
        self.cdb = cdb
        self.vocab = vocab
        self.nlp = None
        self.spell_checker = None
        self.create_pipeline()

    @classmethod
    def load_model_pack(cls, model_path: str):
        model_path = attempt_unpack(model_path)

        cdb_path = os.path.join(model_path, "cdb.dat")
        cdb = CDB.load(cdb_path)

        vocab_path = os.path.join(model_path, "vocab.dat")
        vocab = Vocab.load(vocab_path) if os.path.exists(vocab_path) else None
        config_path = (
            model_path
            if os.path.exists(os.path.join(model_path, "config.json"))
            else None
        )

        if config_path is not None:
            with open(config_path, "r") as f:
                config = json.load(f)
        else:  # inserted
            config = cdb.config

        return cls(cdb, vocab, config)

    def create_pipeline(self) -> Language:
        if self.config is None:
            raise ValueError("Config not loaded. Call load_model_pack() first.")

        self.nlp = spacy.load(
            self.config.general.spacy_model,
            disable=[
                "ner",
                "parser",
                "vectors",
                "textcat",
                "entity_linker",
                "sentencizer",
                "entity_ruler",
                "merge_noun_chunks",
                "merge_entities",
                "merge_subtokens",
            ],
        )

        if self.config.general.spell_check:
            self.spell_checker = BasicSpellChecker(
                cdb_vocab=self.cdb.vocab, config=self.config, data_vocab=self.vocab
            )

        self.nlp.add_pipe(
            "medcat_token_processor", config={"config": self.config.model_dump()}
        )

        # self.nlp.add_pipe('medcat_ner', last=True)

        # self.nlp.add_pipe('medcat_linker', config={'cdb': self.cdb, 'vocab': self.vocab, 'config': self.config})

        return self.nlp

    @lru_cache(maxsize=1000)
    def process(self, text: str) -> "Doc":
        if self.nlp is None:
            raise ValueError("Pipeline not created. Call create_pipeline() first.")
        return self.nlp(text)

    def batch_process(self, texts: List[str], batch_size: int = 32) -> List["Doc"]:
        if self.nlp is None:
            raise ValueError("Pipeline not created. Call create_pipeline() first.")
        return list(self.nlp.pipe(texts, batch_size=batch_size))

    def save_pipeline(self, path: str):
        if self.nlp is None:
            raise ValueError("Pipeline not created. Call create_pipeline() first.")
        self.nlp.to_disk(path)
