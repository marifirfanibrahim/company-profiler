"""
source helpers
shared source utilities
"""

import re
from typing import List, Set

from haystack.dataclasses import Document

from backend.configuration.words import ALL_STOPWORDS


# ==================== QUERY UTILITIES ====================

def extract_query_words(query: str, min_length: int = 3) -> Set[str]:
    # extract words from query
    query_lower = query.lower()
    words = set(re.findall(rf"\b\w{{{min_length},}}\b", query_lower))

    # drop stopwords
    words = words - ALL_STOPWORDS
    return words


def has_any_query_word(text: str, query_words: Set[str], min_matches: int = 1, full_query: str = "") -> bool:
    # check query match
    if not text:
        return False

    # normalize text
    text_lower = text.lower()

    # accept full phrase match
    full = full_query.lower().strip() if full_query else ""
    if full and full in text_lower:
        return True

    # accept empty query list
    if not query_words:
        return True

    # count word hits
    matches = 0
    for word in query_words:
        if word in text_lower:
            matches += 1

    return matches >= min_matches


# ==================== HTML UTILITIES ====================

def clean_html(text: str) -> str:
    # strip html tags
    if not text:
        return ""

    # remove tags
    text = re.sub(r"<[^>]+>", "", text)

    # decode entities
    entities = {
        "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&apos;": "'", "&#8211;": "-", "&#8212;": "-",
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)

    # normalize spaces
    return " ".join(text.split())


# ==================== DOCUMENT UTILITIES ====================

def create_document(
    source_name: str,
    title: str,
    url: str,
    snippet: str,
    content: str = "",
    source_date: str = None,
    **extra_meta
) -> Document:
    # build haystack document
    meta = {
        "title": title,
        "url": url,
        "snippet": snippet[:300] if snippet else "",
        "source": source_name,
        "source_date": source_date,
    }

    # merge extra meta
    meta.update(extra_meta)

    # return document object
    return Document(content=content or snippet, meta=meta)


# ==================== LOGGING ====================

def log_results(source_id: str, documents: List[Document], extra_info: str = None):
    # print results count
    count = len(documents)
    msg = f"[SOURCE] {source_id}: {count} results"
    if extra_info:
        msg += f" ({extra_info})"
    print(msg)


def log_source_status(source_id: str, source_name: str, count: int, extra_info: str = None):
    # print source status
    msg = f"[SOURCE] {source_id} ({source_name}): {count} results"
    if extra_info:
        msg += f" ({extra_info})"
    print(msg)