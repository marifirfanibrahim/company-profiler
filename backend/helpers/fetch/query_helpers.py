"""
build query variants
dedupe query list
limit query count
"""

from typing import List


# ============== NORMALIZE ==============

def normalize_query(text: str) -> str:
    # normalize query text
    s = str(text or "").strip()

    # normalize whitespace
    s = " ".join(s.split())
    return s


def dedupe_queries(queries: List[str]) -> List[str]:
    # dedupe queries by lowercase
    seen = set()
    out: List[str] = []

    for q in queries or []:
        # normalize query
        s = normalize_query(q)
        if not s:
            continue

        # build dedupe key
        key = s.lower()
        if key in seen:
            continue

        # store key and query
        seen.add(key)
        out.append(s)

    return out


# ============== BUILD ==============

def build_expanded_queries(config, query: str, suffixes: List[str]) -> List[str]:
    # build expanded query list
    base = normalize_query(query)
    if not base:
        return []

    # read config flags
    enable = bool(getattr(config, "PIPELINE_ENABLE_QUERY_EXPANSION", False))
    max_q = int(getattr(config, "PIPELINE_QUERY_EXPANSION_MAX_QUERIES", 6))

    # always include base query
    queries: List[str] = [base]

    # stop if disabled
    if not enable:
        return queries

    # add suffix queries
    for suffix in suffixes or []:
        # normalize suffix
        sfx = normalize_query(suffix)
        if not sfx:
            continue

        # build joined query
        full = normalize_query(f"{base} {sfx}")
        queries.append(full)

        # cap size early
        if len(queries) >= max_q:
            break

    # dedupe final list
    queries = dedupe_queries(queries)

    # clamp size after dedupe
    if max_q > 0 and len(queries) > max_q:
        queries = queries[:max_q]

    return queries