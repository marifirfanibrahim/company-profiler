"""
prefer query phrase matches
filter docs by phrase
filter high risk list
"""

from backend.helpers.parse.text_helpers import contains_normalized_phrase, normalize_spaces


# ==================== PHRASE FILTER ====================

def prefer_documents_by_query_phrase(config, query: str, documents: list) -> list:
    # prefer documents matching query phrase
    docs = list(documents or [])
    if not docs:
        return []

    # read toggle flag
    enabled = bool(config.PIPELINE_PHRASE_FILTER_ENABLED)
    if not enabled:
        return docs

    # normalize query
    q = normalize_spaces(query).strip()
    if not q:
        return docs

    # read min chars
    min_chars = int(config.PIPELINE_PHRASE_FILTER_MIN_CHARS)

    # skip short query
    if len(q) < min_chars:
        return docs

    matched = []
    for doc in docs:
        # read meta fields
        meta = getattr(doc, "meta", None) or {}
        title = str(meta.get("title") or "")
        snippet = str(meta.get("snippet") or "")

        # read content field
        content = str(getattr(doc, "content", "") or "")

        # join fields into text
        haystack = f"{title}\n{snippet}\n{content}"

        # check phrase match
        if contains_normalized_phrase(haystack, q):
            matched.append(doc)

    # return matched docs
    if matched:
        return matched

    # return original docs
    return docs


# ==================== PROFILE DOCS ====================

def prefer_documents_by_profile_names(profile: dict, documents: list) -> list:
    # prefer documents matching profile names
    docs = list(documents or [])
    if not docs:
        return []

    names = []

    customer = profile.get("customer") if isinstance(profile, dict) else None
    if isinstance(customer, dict):
        name = normalize_spaces(str(customer.get("name") or "")).strip()
        if name:
            names.append(name)

    guarantor = profile.get("corporate_guarantor") if isinstance(profile, dict) else None
    if isinstance(guarantor, dict):
        name = normalize_spaces(str(guarantor.get("name") or "")).strip()
        if name:
            names.append(name)

    high_risk = profile.get("high_risk_entities") if isinstance(profile, dict) else None
    if isinstance(high_risk, list):
        for item in high_risk:
            if not isinstance(item, dict):
                continue
            name = normalize_spaces(str(item.get("name") or "")).strip()
            if not name:
                continue
            names.append(name)

    if not names:
        return docs

    name_keys = []
    seen = set()
    for n in names:
        key = normalize_spaces(n).lower().strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        name_keys.append(key)

    if not name_keys:
        return docs

    scored = []
    for idx, doc in enumerate(docs):
        meta = getattr(doc, "meta", None) or {}
        title = str(meta.get("title") or "")
        snippet = str(meta.get("snippet") or "")
        content = str(getattr(doc, "content", "") or "")

        hay = normalize_spaces(f"{title} {snippet} {content}").lower()

        hits = 0
        for key in name_keys:
            if key and key in hay:
                hits += 1

        scored.append((hits, idx, doc))

    any_hit = False
    for hits, _, _ in scored:
        if hits > 0:
            any_hit = True
            break

    if not any_hit:
        return docs

    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    out = [d for _, __, d in scored]
    return out


# ==================== HIGH RISK FILTER ====================

def filter_high_risk_entities(config, query: str, profile: dict) -> dict:
    # filter high risk entities that match customer or query
    if not isinstance(profile, dict):
        return profile

    # read toggle flag
    enabled = bool(config.PIPELINE_HIGH_RISK_FILTER_ENABLED)
    if not enabled:
        return profile

    # read customer block
    customer = profile.get("customer")
    if not isinstance(customer, dict):
        customer = {}

    # read high risk list
    items = profile.get("high_risk_entities")
    if not isinstance(items, list):
        items = []

    # normalize query
    q = normalize_spaces(query).lower().strip()

    # normalize customer name
    cust_name = normalize_spaces(str(customer.get("name") or "")).lower().strip()

    # read min chars
    min_chars = int(config.PIPELINE_HIGH_RISK_SELF_MIN_CHARS)

    cleaned = []
    dropped = 0

    for item in items:
        # validate item type
        if not isinstance(item, dict):
            dropped += 1
            continue

        # normalize name
        name = normalize_spaces(str(item.get("name") or "")).strip()
        if not name:
            dropped += 1
            continue

        # normalize name for match
        name_low = name.lower()

        # drop direct query match
        if q and name_low == q:
            dropped += 1
            continue

        # drop direct customer match
        if cust_name and name_low == cust_name:
            dropped += 1
            continue

        # drop customer prefix match
        if cust_name and len(name_low) >= min_chars and cust_name.startswith(name_low):
            dropped += 1
            continue

        # keep item
        cleaned.append(item)

    # print drop count
    if dropped:
        print(f"[PIPELINE] high risk filter: dropped {dropped} items")

    # store filtered list
    profile["high_risk_entities"] = cleaned
    return profile