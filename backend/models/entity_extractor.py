"""
extract named entities from text
wrap gliner model for ner
identify persons and organizations
deduplicate similar entities
score entity confidence
"""

import re
from difflib import SequenceMatcher
from typing import List, Dict, Any

from gliner import GLiNER
from haystack.core.component import component
from haystack.core.serialization import default_from_dict, default_to_dict


# ==================== ENTITY EXTRACTOR COMPONENT ====================

@component
class EntityExtractor:


    # ------------------ INITIALIZATION ------------------

    def __init__(self, config):
        # store configuration reference
        self.config = config

        # set model name from config
        self.model_name = config.GLINER_MODEL

        # print initialization message
        print(f"[ENTITY] Model: {self.model_name}")

        # set entity labels from config
        self.labels = config.GLINER_LABELS

        # load default threshold from config
        self.threshold = config.GLINER_THRESHOLD

        # load pretrained gliner model
        self.model = GLiNER.from_pretrained(self.model_name)

        # print load status
        print("[ENTITY] gliner model loaded")


    # ------------------ SERIALIZATION ------------------

    def to_dict(self) -> Dict[str, Any]:
        # serialize component to dictionary
        return default_to_dict(self, config=self.config)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityExtractor":
        # deserialize component from dictionary
        return default_from_dict(cls, data)


    # ------------------ COMPONENT INTERFACE ------------------

    @component.output_types(entities=List[Dict[str, Any]])
    def run(self, text: str, threshold: float = None) -> Dict[str, Any]:
        # stop on missing model or text
        if not self.model or not text:
            return {"entities": []}

        # remove parenthetical content
        clean_text = re.sub(r"\s*\(.*?\)", "", text)

        # select threshold value
        current_threshold = threshold if threshold is not None else self.threshold

        # run gliner prediction
        predictions = self.model.predict_entities(
            clean_text,
            self.labels,
            threshold=current_threshold,
            flat_ner=True
        )

        # print prediction count
        print(f"[ENTITY] raw predictions count: {len(predictions) if predictions is not None else 0}")

        # print empty prediction status
        if not predictions:
            print("[ENTITY] no entities predicted by GLiNER")

        entities: List[Dict[str, Any]] = []

        for p in predictions:
            # append entity row
            entities.append({
                "name": p.get("text", ""),
                "type": p.get("label", ""),
                "score": round(float(p.get("score", 0.0)), 2)
            })

        # dedupe similar entities
        deduplicated = self._deduplicate_entities(entities)

        return {"entities": deduplicated}


    # ------------------ DEDUPLICATION ------------------

    def _deduplicate_entities(self, entities: List[Dict[str, Any]], threshold: float = 0.75) -> List[Dict[str, Any]]:
        # sort by score descending
        entities_sorted = sorted(entities, key=lambda x: x["score"], reverse=True)

        final_entities: List[Dict[str, Any]] = []

        for entity in entities_sorted:
            # read entity fields
            name = entity.get("name", "")
            ent_type = entity.get("type", "")
            if not name or not ent_type:
                continue

            # track duplicate flag
            is_duplicate = False

            for final_entity in final_entities:
                # skip type mismatch
                if final_entity.get("type") != ent_type:
                    continue

                # compute similarity ratio
                existing_name = final_entity.get("name", "")
                similarity = SequenceMatcher(
                    None,
                    name.lower(),
                    existing_name.lower()
                ).ratio()

                # mark duplicate match
                if similarity > threshold:
                    is_duplicate = True
                    break

            # append unique entity
            if not is_duplicate:
                final_entities.append(entity)

        return final_entities