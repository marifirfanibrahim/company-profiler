"""
build snapshot
summarize company news
use llm generator
"""

import re
from typing import List

from haystack.dataclasses import Document

from backend.configuration.prompts import SNAPSHOT_TEMPLATE
from backend.helpers.logic.helper import get_system_prompt


# ==================== SNAPSHOT EXTRACTOR ====================

class SnapshotExtractor:


    # ------------------ INITIALIZATION ------------------

    def __init__(self, config):
        # store configuration reference
        self.config = config

        # load limits from config
        self.max_docs = config.SUMMARIZATION_MAX_DOCS
        self.max_chars_per_doc = config.SNAPSHOT_MAX_DOC_CHARS

        # print init status
        print(f"[SNAPSHOT] initialized (max_docs: {self.max_docs})")


    # ------------------ PROMPT BUILDING ------------------

    def _build_documents_block(self, documents: List[Document]) -> str:
        # format documents into prompt block
        lines: List[str] = []

        # clamp docs list
        limited_docs = documents[: self.max_docs]

        for idx, doc in enumerate(limited_docs, start=1):
            # read meta fields
            meta = doc.meta or {}
            title = meta.get("title", "Untitled")
            source = meta.get("source", "Unknown")
            date = meta.get("source_date", "N/A")
            url = meta.get("url", "#")

            # truncate content into snippet
            content = doc.content or ""
            snippet = content[: self.max_chars_per_doc].replace("\n", " ").strip()

            # write doc lines
            lines.append(f"[{idx}] Source: {source} | Title: {title} | Date: {date} | URL: {url}")
            lines.append(f"    Content: {snippet}")
            lines.append("---")

        return "\n".join(lines)

    def _build_prompt(self, company: str, documents: List[Document]) -> str:
        # build full snapshot prompt text
        system_prompt = get_system_prompt()
        docs_block = self._build_documents_block(documents)

        # format template string
        prompt = SNAPSHOT_TEMPLATE.format(
            system_prompt=system_prompt,
            company=company,
            documents_block=docs_block,
        )
        return prompt

    def _trim_to_full_sentence(self, text: str) -> str:
        # trim snapshot to last full sentence
        s = str(text or "").strip()
        if not s:
            return s

        # find last sentence terminator
        last_dot = s.rfind(".")
        last_q = s.rfind("?")
        last_ex = s.rfind("!")
        last = max(last_dot, last_q, last_ex)

        # return full string on no terminator
        if last == -1:
            return s

        return s[: last + 1].strip()

    def _strip_preface(self, text: str) -> str:
        # remove common llm preface
        s = str(text or "").strip()
        if not s:
            return ""

        # strip known prefixes
        s = re.sub(r"^\s*the requested narrative snapshot\s*:\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^\s*the requested output\s*:\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^\s*requested output\s*:\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^\s*here is the narrative snapshot\s*:\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^\s*here is the snapshot\s*:\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^\s*here is\s+", "", s, flags=re.IGNORECASE)

        return s.strip()


    # ------------------ PUBLIC INTERFACE ------------------

    def run(self, company: str, documents: List[Document], llm) -> str:
        # generate snapshot text using llm
        if not llm or not documents:
            return ""

        # build prompt string
        prompt = self._build_prompt(company=company, documents=documents)

        # read generation limits
        max_tokens = self.config.SNAPSHOT_MAX_TOKENS
        timeout = self.config.LLM_TIMEOUT

        # run llm call
        result = llm.run(
            prompt=prompt,
            max_tokens=max_tokens,
            timeout=timeout,
        )

        # read reply text
        replies = result.get("replies") or []
        text = replies[0] if replies else ""
        if not text:
            return ""

        # strip prefacing text
        snapshot = self._strip_preface(str(text).strip())

        # trim to full sentence end
        snapshot = self._trim_to_full_sentence(snapshot)
        return snapshot