"""
extract profiles
build structured json
use llm generator
"""

import json
from typing import List, Dict, Any

from haystack.dataclasses import Document

from backend.configuration.prompts import PROFILE_TEMPLATE
from backend.helpers.logic.helper import get_system_prompt
from backend.helpers.persist.json_utils import extract_first_json_object


# ==================== PROFILE EXTRACTOR ====================

class ProfileExtractor:


    # ------------------ INITIALIZATION ------------------

    def __init__(self, config):
        # store configuration reference
        self.config = config

        # load limits from config
        self.max_docs = config.SUMMARIZATION_MAX_DOCS
        self.max_chars_per_doc = config.PROFILE_MAX_DOC_CHARS
        self.max_entities = config.PROFILE_MAX_ENTITIES_FOR_CONTEXT
        self.max_relationships = config.PROFILE_MAX_RELATIONSHIPS_FOR_CONTEXT

        # print init status
        print(f"[PROFILE] initialized (max_docs: {self.max_docs})")


    # ------------------ PROMPT BUILDING ------------------

    def _build_documents_block(self, documents: List[Document]) -> str:
        # format documents into prompt block
        lines: List[str] = []

        # clamp docs list
        limited_docs = documents[: self.max_docs]

        for idx, doc in enumerate(limited_docs, start=1):
            # read doc meta
            meta = doc.meta or {}
            title = meta.get("title", "Untitled")
            source = meta.get("source", "Unknown")
            date = meta.get("source_date", "N/A")
            url = meta.get("url", "#")

            # clamp doc content
            content = doc.content or ""
            snippet = content[: self.max_chars_per_doc].replace("\n", " ").strip()

            # append header line
            lines.append(f"[{idx}] Source: {source} | Title: {title} | Date: {date} | URL: {url}")

            # append content line
            lines.append(f"    Content: {snippet}")

            # append divider
            lines.append("---")

        return "\n".join(lines)

    def _build_context_block(
        self,
        company: str,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> str:
        # format entities and relationships into compact context block
        lines: List[str] = []

        # normalize company string
        company_lower = (company or "").lower().strip()

        filtered_entities: List[Dict[str, Any]] = []
        for ent in entities or []:
            # read entity fields
            name = ent.get("name", "")
            ent_type = ent.get("type", "")

            # filter invalid fields
            if not name or not ent_type:
                continue
            if ent_type.upper() not in ["PERSON", "ORG"]:
                continue

            filtered_entities.append(ent)

        # sort entities by score
        filtered_entities.sort(key=lambda e: float(e.get("score", 0.0) or 0.0), reverse=True)
        top_entities = filtered_entities[: self.max_entities]

        if top_entities:
            # append entities header
            lines.append("ENTITIES:")

            for ent in top_entities:
                # read entity row
                name = str(ent.get("name", "")).strip()
                ent_type = str(ent.get("type", "")).strip()
                score_val = float(ent.get("score", 0.0) or 0.0)

                # append entity line
                lines.append(f"- {ent_type}: {name} | score={score_val:.2f}")

            # append spacer
            lines.append("")

        filtered_rels: List[Dict[str, Any]] = []
        for rel in relationships or []:
            # read relationship fields
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("relationship_type", "")

            # skip invalid rel
            if not source or not target or not rel_type:
                continue

            filtered_rels.append(rel)

        def rel_key(r):
            # build sort key for relationship
            src = str(r.get("source", "")).lower()
            tgt = str(r.get("target", "")).lower()
            conf = float(r.get("confidence", 0.0) or 0.0)
            direct = 1 if (company_lower and (company_lower in src or company_lower in tgt)) else 0
            return (direct, conf)

        # sort relationships by directness and confidence
        filtered_rels.sort(key=rel_key, reverse=True)
        top_rels = filtered_rels[: self.max_relationships]

        if top_rels:
            # append rel header
            lines.append("RELATIONSHIPS:")

            for rel in top_rels:
                # read rel row
                src = str(rel.get("source", "")).strip()
                tgt = str(rel.get("target", "")).strip()
                rel_type = str(rel.get("relationship_type", "")).strip()
                conf_val = float(rel.get("confidence", 0.0) or 0.0)

                # append rel line
                lines.append(f"- {src} --[{rel_type}]--> {tgt} | confidence={conf_val:.2f}")

            # append spacer
            lines.append("")

        # return none marker
        if not lines:
            return "none"

        return "\n".join(lines)

    def _build_prompt(
        self,
        company: str,
        documents: List[Document],
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> str:
        # build full profile prompt text
        system_prompt = get_system_prompt()
        docs_block = self._build_documents_block(documents)
        context_block = self._build_context_block(
            company=company,
            entities=entities,
            relationships=relationships,
        )

        # format template string
        prompt = PROFILE_TEMPLATE.format(
            system_prompt=system_prompt,
            company=company,
            documents_block=docs_block,
            context_block=context_block,
        )
        return prompt

    def _strip_code_fences(self, text: str) -> str:
        # remove markdown code fences from llm reply
        if not text:
            return ""

        stripped = text.lstrip()
        if not stripped.startswith("```"):
            return text

        # strip opening fence
        body = stripped[3:]
        if body.lower().startswith("json"):
            body = body[4:]

        # strip leading newlines
        while body.startswith("\n") or body.startswith("\r"):
            body = body[1:]

        # strip closing fence
        closing = body.rfind("```")
        if closing != -1:
            body = body[:closing]

        return body.strip()

    def _looks_like_valid_json_object(self, text: str) -> bool:
        # quick structural check for json
        if not text:
            return False

        s = text.strip()

        # check braces
        if not s.startswith("{") or not s.endswith("}"):
            return False

        depth = 0
        in_string = False
        escape = False

        for ch in s:
            if escape:
                escape = False
                continue

            if ch == "\\":
                if in_string:
                    escape = True
                continue

            if ch == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    return False

        if in_string:
            return False
        if depth != 0:
            return False

        return True


    # ------------------ PUBLIC INTERFACE ------------------

    def run(
        self,
        company: str,
        documents: List[Document],
        llm,
        entities: List[Dict[str, Any]] = None,
        relationships: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # generate structured profile json using llm
        if not llm or not documents:
            return {
                "customer": {},
                "corporate_guarantor": {},
                "high_risk_entities": [],
            }

        # normalize lists
        ent_list = list(entities or [])
        rel_list = list(relationships or [])

        # build prompt string
        prompt = self._build_prompt(
            company=company,
            documents=documents,
            entities=ent_list,
            relationships=rel_list,
        )

        # read generation limits
        max_tokens = self.config.PROFILE_MAX_TOKENS
        timeout = self.config.LLM_TIMEOUT

        # run llm call
        result = llm.run(
            prompt=prompt,
            max_tokens=max_tokens,
            timeout=timeout,
        )

        # read reply text
        replies = result.get("replies") or []
        raw = replies[0] if replies else ""
        if not raw:
            return {
                "customer": {},
                "corporate_guarantor": {},
                "high_risk_entities": [],
            }

        # normalize reply body
        text = str(raw).strip()
        text = self._strip_code_fences(text)

        # extract json object substring
        json_text = extract_first_json_object(text)
        if not json_text:
            return {
                "customer": {},
                "corporate_guarantor": {},
                "high_risk_entities": [],
            }

        # validate json structure
        if not self._looks_like_valid_json_object(json_text):
            return {
                "customer": {},
                "corporate_guarantor": {},
                "high_risk_entities": [],
            }

        # parse json into dict
        data = json.loads(json_text)
        if not isinstance(data, dict):
            return {
                "customer": {},
                "corporate_guarantor": {},
                "high_risk_entities": [],
            }

        # read customer block
        customer = data.get("customer")
        if not isinstance(customer, dict):
            customer = {}

        # read guarantor block
        corporate_guarantor = data.get("corporate_guarantor")
        if not isinstance(corporate_guarantor, dict):
            corporate_guarantor = {}

        # read high risk list
        high_risk = data.get("high_risk_entities")
        if not isinstance(high_risk, list):
            high_risk = []

        return {
            "customer": customer,
            "corporate_guarantor": corporate_guarantor,
            "high_risk_entities": high_risk,
        }