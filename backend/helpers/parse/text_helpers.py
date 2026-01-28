"""
normalize text spaces
match phrases
build lookup keys
"""

import re


# ==================== NORMALIZE ====================

def normalize_spaces(text: str) -> str:
    # normalize whitespace runs
    s = str(text or "")
    s = " ".join(s.split())
    return s


# ==================== CLEAN ====================

def clean_block_text(text: str) -> str:
    # normalize text blocks
    s = str(text or "")

    # normalize line breaks
    s = s.replace("\r", "\n")

    # collapse spaces and tabs
    s = re.sub(r"[ \t]+", " ", s)

    # collapse blank lines
    s = re.sub(r"\n\s*\n+", "\n\n", s)

    return s.strip()


# ==================== MATCH ====================

def contains_normalized_phrase(text: str, phrase: str) -> bool:
    # check phrase in normalized text
    p = normalize_spaces(phrase).lower()
    if not p:
        return True

    # normalize haystack
    t = normalize_spaces(text).lower()
    return p in t


# ==================== LOOKUP ====================

def normalize_lookup_key(text: str) -> str:
    # normalize key for mapping
    s = normalize_spaces(text).lower()
    if not s:
        return ""

    # drop symbols
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = normalize_spaces(s)

    # drop suffix tokens
    drop = [
        "berhad",
        "bhd",
        "had",
        "plc",
        "limited",
        "ltd",
        "sdn",
        "bhds",
        "sdn bhd",
    ]

    for w in drop:
        # remove token
        s = s.replace(w, " ")

    # normalize final key
    s = normalize_spaces(s)
    return s