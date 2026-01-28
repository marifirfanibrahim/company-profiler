"""
store helpers
document metadata tools
"""

from typing import Dict, Any


# ==================== META HELPERS ====================

def sanitize_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    # keep supported meta types
    allowed_types = (str, int, float, bool)
    cleaned: Dict[str, Any] = {}

    for key, value in (meta or {}).items():
        # keep allowed types
        if isinstance(value, allowed_types):
            cleaned[key] = value
        elif value is None:
            continue
        else:
            # stringify unsupported types
            cleaned[key] = str(value)

    return cleaned


# ==================== PROFILE DOCS ====================

def clamp_profile_documents(config, documents: list) -> list:
    # clamp documents for sqlite storage
    if not bool(config.PROFILES_STORE_DOCUMENTS):
        return []

    # normalize list input
    docs = list(documents or [])
    if not docs:
        return []

    # read caps from config
    max_docs = int(config.PROFILES_STORE_DOCUMENTS_MAX_DOCS)
    max_chars = int(config.PROFILES_STORE_DOCUMENTS_MAX_CONTENT_CHARS)

    out = []

    for item in docs[:max_docs]:
        # read content value
        content = str(item.get("content") or "")

        # clamp content chars
        if max_chars > 0 and len(content) > max_chars:
            content = content[:max_chars]

        # read meta value
        meta_in = item.get("meta") or {}

        # sanitize meta types
        meta = sanitize_meta(meta_in)

        # append normalized row
        out.append(
            {
                "content": content,
                "meta": meta,
            }
        )

    return out