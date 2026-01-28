"""
extract relations
use glirel model
produce relation triples
"""

import re
from typing import List, Dict, Any

from glirel import GLiREL
from haystack.core.component import component
from haystack.core.serialization import default_from_dict, default_to_dict

from backend.configuration.words import RELATIONSHIP_STOPWORDS


# ================ RELATIONSHIP EXTRACTOR COMPONENT ================

@component
class RelationshipExtractor:


    # -------------- INITIALIZATION --------------

    def __init__(self, config):
        # store configuration reference
        self.config = config

        # set model name from config
        self.model_name = config.GLIREL_MODEL

        # print initialization message
        print(f"[RELATIONSHIP] Model: {self.model_name}\n")

        # set relationship labels from config
        self.labels = config.GLIREL_LABELS

        # load threshold from config
        self.threshold = config.GLIREL_THRESHOLD

        # load stopwords from config
        self.stopwords = RELATIONSHIP_STOPWORDS

        # load pretrained glirel model
        self.model = GLiREL.from_pretrained(self.model_name)

        # print load message
        print("[RELATIONSHIP] glirel model loaded\n")


    # ------------------ SERIALIZATION ------------------

    def to_dict(self) -> Dict[str, Any]:
        # serialize component to dictionary
        return default_to_dict(self, config=self.config)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationshipExtractor":
        # deserialize component from dictionary
        return default_from_dict(cls, data)


    # -------------- COMPONENT INTERFACE --------------

    @component.output_types(relationships=List[Dict[str, Any]])
    def run(self, text: str, entities: list = None) -> Dict[str, Any]:
        # stop on missing model
        if not self.model:
            print("[RELATIONSHIP] model not loaded")
            return {"relationships": []}

        # stop on missing text
        if not text:
            print("[RELATIONSHIP] no text provided")
            return {"relationships": []}

        # stop on low entity count
        if not entities or len(entities) < 2:
            count = len(entities) if entities else 0
            print(f"[RELATIONSHIP] insufficient entities: {count}")
            return {"relationships": []}

        # remove parenthetical content from text
        clean_text = re.sub(r"\s*\(.*?\)", "", text)

        # tokenize text into words
        tokens = clean_text.split()

        # truncate to max tokens from config
        max_tokens = self.config.GLIREL_MAX_TOKENS
        if len(tokens) > max_tokens:
            tokens = tokens[:max_tokens]

        # rejoin for searching
        text_joined = " ".join(tokens)
        text_lower = text_joined.lower()

        # build ner list for glirel
        ner_data = []

        for ent in entities:
            # read entity fields
            ent_name = ent.get("name", "")
            ent_type = ent.get("type", "")

            # validate entity fields
            if not ent_name or not ent_type:
                continue

            # locate entity in text
            ent_lower = ent_name.lower()
            start_char = text_lower.find(ent_lower)
            if start_char == -1:
                continue

            # compute token start
            prefix_text = text_joined[:start_char]
            token_start = len(prefix_text.split())
            if prefix_text and not prefix_text.endswith(" "):
                token_start = max(0, token_start - 1)

            # compute token end
            entity_tokens = ent_name.split()
            token_end = token_start + len(entity_tokens) - 1
            token_end = min(token_end, len(tokens) - 1)

            # append ner row
            ner_data.append([token_start, token_end, ent_type, ent_name])

        # stop on low ner coverage
        if len(ner_data) < 2:
            print(f"[RELATIONSHIP] only {len(ner_data)} entities found in text")
            return {"relationships": []}

        # print extraction status
        print(f"\n[ENTITIES] extracting from {len(tokens)} tokens, {len(ner_data)} entities")

        # predict relations
        relations = self.model.predict_relations(
            tokens,
            labels=self.labels,
            threshold=self.threshold,
            ner=ner_data,
            top_k=self.config.GLIREL_TOP_K
        )

        relationships: List[Dict[str, Any]] = []
        low_confidence_removed = 0

        for rel in relations:
            # read head and tail token ranges
            head_pos = rel.get("head_pos", [0, 0])
            tail_pos = rel.get("tail_pos", [0, 0])

            # init resolved names
            head_name = None
            tail_name = None

            for ner_item in ner_data:
                # unpack ner row
                ner_start, ner_end, ner_type, ner_name = ner_item

                # map head match
                if head_pos[0] == ner_start and head_pos[1] == ner_end:
                    head_name = ner_name

                # map tail match
                if tail_pos[0] == ner_start and tail_pos[1] == ner_end:
                    tail_name = ner_name

            # build head fallback
            if not head_name:
                head_text = rel.get("head_text", [])
                if isinstance(head_text, list):
                    head_name = " ".join(head_text)
                else:
                    head_name = str(head_text)

            # build tail fallback
            if not tail_name:
                tail_text = rel.get("tail_text", [])
                if isinstance(tail_text, list):
                    tail_name = " ".join(tail_text)
                else:
                    tail_name = str(tail_text)

            # normalize whitespace
            head_name = head_name.strip()
            tail_name = tail_name.strip()

            # drop possessives
            head_name = re.sub(r"\b(\w+)'s$", r"\1", head_name)
            tail_name = re.sub(r"\b(\w+)'s$", r"\1", tail_name)

            # strip quote chars
            head_name = head_name.strip(' \t\n\r\"\'')
            tail_name = tail_name.strip(' \t\n\r\"\'')
            
            # validate head entity
            if not self._is_valid_entity(head_name):
                continue

            # validate tail entity
            if not self._is_valid_entity(tail_name):
                continue

            # skip self links
            if head_name.lower() == tail_name.lower():
                continue

            # read label and score
            label = rel.get("label", "related to")
            score = float(rel.get("score", 0.0) or 0.0)

            # enforce confidence gate
            min_conf = self.config.TOP_RELATIONSHIP_MIN_CONFIDENCE
            if score < min_conf:
                low_confidence_removed += 1
                continue

            # append relationship row
            relationships.append({
                "source": head_name,
                "target": tail_name,
                "relationship_type": label,
                "confidence": round(score, 2)
            })

        # dedupe relationships
        seen = set()
        unique_relationships: List[Dict[str, Any]] = []
        for rel in relationships:
            # build dedupe key
            key = (rel["source"].lower(), rel["target"].lower(), rel["relationship_type"])
            if key in seen:
                continue
            seen.add(key)
            unique_relationships.append(rel)

        # print summary
        if unique_relationships:
            print(f"[RELATIONSHIP] found {len(unique_relationships)} valid relationships (removed {low_confidence_removed} low-confidence)")
        else:
            print(f"[RELATIONSHIP] no valid relationships above threshold {self.threshold} (removed {low_confidence_removed} low-confidence)")

        return {"relationships": unique_relationships}

    def _is_valid_entity(self, name: str) -> bool:
        # validate entity name against stopwords
        if not name or name == "-":
            return False

        # reject short strings
        if len(name) < 2:
            return False

        # reject stopword-only strings
        name_words = set(name.lower().split())
        if name_words.issubset(self.stopwords):
            return False

        # reject direct stopword hits
        if name.lower() in self.stopwords:
            return False

        return True