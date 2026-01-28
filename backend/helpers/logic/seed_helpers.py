"""
seed expansion helpers
extract evidence backed entities
store candidate list
promote into seed list
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Any

from backend.configuration.paths import SEED_ENTITIES_PATH, SEED_ENTITY_CANDIDATES_PATH
from backend.configuration.seeding import (
    SEED_EXPANSION_ENABLED,
    SEED_EXPANSION_MAX_CANDIDATES_PER_PROFILE,
    SEED_EXPANSION_MAX_CUSTOMER_GUARANTOR_PER_PROFILE,
    SEED_EXPANSION_MAX_HIGH_RISK_PER_PROFILE,
    SEED_EXPANSION_MIN_MENTIONS,
    SEED_EXPANSION_MIN_CONTEXT_HITS,
    SEED_EXPANSION_CONTEXT_WINDOW_CHARS,
    SEED_EXPANSION_PROMOTE_MIN_SCORE,
    SEED_EXPANSION_MAX_PROMOTIONS_PER_RUN,
    SEED_EXPANSION_CUSTOMER_KEYWORDS,
    SEED_EXPANSION_GUARANTOR_KEYWORDS,
    SEED_EXPANSION_HIGH_RISK_KEYWORDS,
)
from backend.helpers.persist.json_utils import load_json, save_json
from backend.helpers.parse.text_helpers import normalize_spaces, normalize_lookup_key


# ==================== NORMALIZE ====================

def normalize_entity_name(value: str) -> str:
    # normalize entity name
    s = normalize_spaces(str(value or ""))
    if not s:
        return ""

    # strip quotes
    if s.startswith('"'):
        s = s[1:].strip()
    if s.endswith('"'):
        s = s[:-1].strip()

    # normalize final name
    return normalize_spaces(s)


def entity_key(value: str) -> str:
    # build lookup key
    return normalize_lookup_key(normalize_entity_name(value))


def is_same_entity(a: str, b: str) -> bool:
    # match entities by lookup keys
    ak = entity_key(a)
    bk = entity_key(b)

    # stop on missing keys
    if not ak or not bk:
        return False

    # check full match
    if ak == bk:
        return True

    # check containment match
    if ak in bk or bk in ak:
        return True

    return False


# ==================== MATCH ====================

def _tokenize_for_regex(name: str) -> List[str]:
    # build tokens for regex
    s = str(name or "").lower()

    # drop punctuation
    s = re.sub(r"[^a-z0-9\s]+", " ", s)

    # normalize whitespace
    s = normalize_spaces(s)

    # stop on empty token stream
    if not s:
        return []

    # split tokens
    parts = [p for p in s.split(" ") if p]
    return parts


def build_entity_regex(name: str):
    # build entity regex
    tokens = _tokenize_for_regex(name)
    if not tokens:
        return None

    # join tokens with gap matcher
    mid = r"[\s\W]+".join([re.escape(t) for t in tokens])

    # build full word boundary pattern
    pat = rf"\b{mid}\b"
    return re.compile(pat, flags=re.IGNORECASE)


def count_entity_mentions(text: str, name: str) -> int:
    # count entity mentions
    rx = build_entity_regex(name)
    if rx is None:
        return 0

    # normalize text
    s = str(text or "")
    if not s.strip():
        return 0

    # count regex matches
    hits = list(rx.finditer(s))
    return int(len(hits))


def count_entity_context_hits(text: str, name: str, keywords: List[str], window_chars: int) -> int:
    # count keyword hits near entity mentions
    rx = build_entity_regex(name)
    if rx is None:
        return 0

    # normalize text
    s = str(text or "")
    if not s.strip():
        return 0

    # normalize keyword list
    kw = []
    for k in keywords or []:
        kk = normalize_spaces(str(k or "")).lower()
        if not kk:
            continue
        kw.append(kk)

    # stop on empty keywords
    if not kw:
        return 0

    # normalize window size
    w = int(window_chars)
    if w <= 0:
        w = 140

    hits = 0
    for m in rx.finditer(s):
        # compute context window slice
        start = max(0, int(m.start()) - w)
        end = min(len(s), int(m.end()) + w)
        ctx = s[start:end].lower()

        # match any keyword
        ok = False
        for k in kw:
            if k in ctx:
                ok = True
                break

        # count hit
        if ok:
            hits += 1

    return int(hits)


# ==================== CANDIDATES ====================

def _doc_evidence_key(meta: dict) -> str:
    # build evidence key
    m = meta or {}

    # normalize fields
    url = normalize_spaces(str(m.get("url") or ""))
    title = normalize_spaces(str(m.get("title") or ""))
    source = normalize_spaces(str(m.get("source") or ""))
    date = normalize_spaces(str(m.get("source_date") or ""))

    # build stable key
    return f"{url}|{title}|{source}|{date}"


def _extract_candidate_from_profile(profile: dict, role: str) -> str:
    # extract name from role object
    if not isinstance(profile, dict):
        return ""

    # select role object
    if role == "customer":
        obj = profile.get("customer")
    else:
        obj = profile.get("corporate_guarantor")

    # validate role type
    if not isinstance(obj, dict):
        return ""

    # normalize name field
    return normalize_entity_name(obj.get("name"))


def _extract_high_risk_names_from_profile(profile: dict) -> List[str]:
    # extract high risk names
    if not isinstance(profile, dict):
        return []

    # read list field
    items = profile.get("high_risk_entities")
    if not isinstance(items, list):
        return []

    out: List[str] = []
    seen = set()

    for item in items:
        # validate item type
        if not isinstance(item, dict):
            continue

        # normalize name field
        name = normalize_entity_name(item.get("name"))
        if not name:
            continue

        # dedupe by lowercase
        key = name.lower()
        if key in seen:
            continue

        seen.add(key)
        out.append(name)

    return out


def _compute_candidate_score(mentions: int, context_hits: int) -> float:
    # compute candidate score
    min_m = int(SEED_EXPANSION_MIN_MENTIONS)
    if min_m <= 0:
        min_m = 1

    # read min context hits
    min_c = int(SEED_EXPANSION_MIN_CONTEXT_HITS)

    # normalize counters
    m = int(mentions)
    c = int(context_hits)

    # compute mention score
    m_score = float(min(1.0, float(m) / float(min_m)))

    if min_c <= 0:
        # cap mention only score
        score = float(min(0.60, 0.60 * m_score))
        return float(max(0.0, min(1.0, score)))

    # compute context score
    c_score = float(min(1.0, float(c) / float(max(1, min_c))))

    # compute weighted score
    score = float((0.60 * c_score) + (0.40 * m_score))
    score = float(max(0.0, min(1.0, score)))

    return float(score)


def _score_and_build_candidate(
    query_name: str,
    role: str,
    name: str,
    keywords: List[str],
    documents: list,
    stamp: str,
) -> Dict[str, Any]:
    # score candidate using evidence
    mention_total = 0
    context_total = 0

    evidence = []
    seen_e = set()

    for doc in documents or []:
        # read content and meta
        content = str(getattr(doc, "content", "") or "")
        meta = getattr(doc, "meta", None) or {}

        # count mention hits
        mentions = count_entity_mentions(content, name)
        if mentions <= 0:
            continue

        # count context hits
        ctx_hits = count_entity_context_hits(
            text=content,
            name=name,
            keywords=keywords,
            window_chars=int(SEED_EXPANSION_CONTEXT_WINDOW_CHARS),
        )

        # aggregate counters
        mention_total += int(mentions)
        context_total += int(ctx_hits)

        # build evidence key
        ek = _doc_evidence_key(meta)
        if ek in seen_e:
            continue

        # store evidence row
        seen_e.add(ek)
        evidence.append(
            {
                "url": str(meta.get("url") or ""),
                "title": str(meta.get("title") or ""),
                "source": str(meta.get("source") or ""),
                "source_date": meta.get("source_date"),
            }
        )

    # enforce mentions gate
    min_m = int(SEED_EXPANSION_MIN_MENTIONS)
    if min_m <= 0:
        min_m = 1
    if int(mention_total) < int(min_m):
        return {}

    # enforce context gate
    min_c = int(SEED_EXPANSION_MIN_CONTEXT_HITS)
    if min_c > 0 and int(context_total) < int(min_c):
        return {}

    # compute score
    score = _compute_candidate_score(mentions=mention_total, context_hits=context_total)

    return {
        "name": name,
        "role": role,
        "roles": [role],
        "score": float(round(score, 3)),
        "mentions": int(mention_total),
        "context_hits": int(context_total),
        "evidence": evidence,
        "source_query": query_name,
        "first_seen_at": stamp,
        "last_seen_at": stamp,
        "promoted_at": None,
    }


def extract_seed_candidates_from_profile(query: str, profile: dict, documents: list) -> List[Dict[str, Any]]:
    # extract candidates with evidence
    if not bool(SEED_EXPANSION_ENABLED):
        return []

    # normalize query name
    q = normalize_entity_name(query)
    if not q:
        return []

    out: List[Dict[str, Any]] = []
    stamp = datetime.now(timezone.utc).isoformat()

    # normalize caps
    max_total = int(SEED_EXPANSION_MAX_CANDIDATES_PER_PROFILE)
    if max_total <= 0:
        max_total = 12

    max_cg = int(SEED_EXPANSION_MAX_CUSTOMER_GUARANTOR_PER_PROFILE)
    if max_cg <= 0:
        max_cg = 6

    max_hr = int(SEED_EXPANSION_MAX_HIGH_RISK_PER_PROFILE)
    if max_hr <= 0:
        max_hr = 8

    # build role plan
    cg_roles = [
        ("customer", list(SEED_EXPANSION_CUSTOMER_KEYWORDS or [])),
        ("guarantor", list(SEED_EXPANSION_GUARANTOR_KEYWORDS or [])),
    ]

    cg_count = 0
    for role, keywords in cg_roles:
        # read candidate name
        name = _extract_candidate_from_profile(profile, role)
        if not name:
            continue

        # block query entity
        if is_same_entity(name, q):
            continue

        # score candidate
        item = _score_and_build_candidate(
            query_name=q,
            role=role,
            name=name,
            keywords=keywords,
            documents=documents,
            stamp=stamp,
        )
        if not item:
            continue

        # append candidate
        out.append(item)
        cg_count += 1

        # enforce role cap
        if cg_count >= max_cg:
            break

        # enforce global cap
        if len(out) >= max_total:
            return out[:max_total]

    # build high risk candidates
    hr_keywords = list(SEED_EXPANSION_HIGH_RISK_KEYWORDS or [])
    hr_names = _extract_high_risk_names_from_profile(profile)

    hr_count = 0
    for name in hr_names:
        # block query entity
        if is_same_entity(name, q):
            continue

        # block duplicates already added
        dup = False
        for existing in out:
            if is_same_entity(str(existing.get("name") or ""), name):
                dup = True
                break
        if dup:
            continue

        # score candidate
        item = _score_and_build_candidate(
            query_name=q,
            role="high_risk",
            name=name,
            keywords=hr_keywords,
            documents=documents,
            stamp=stamp,
        )
        if not item:
            continue

        # append candidate
        out.append(item)
        hr_count += 1

        # enforce role cap
        if hr_count >= max_hr:
            break

        # enforce global cap
        if len(out) >= max_total:
            break

    return out[:max_total]


def load_seed_entity_candidates() -> List[Dict[str, Any]]:
    # load candidates file
    data = load_json(SEED_ENTITY_CANDIDATES_PATH, default=[])
    if not isinstance(data, list):
        return []

    out = []
    for item in data:
        # validate item type
        if not isinstance(item, dict):
            continue
        out.append(item)

    return out


def save_seed_entity_candidates(items: List[Dict[str, Any]]) -> bool:
    # save candidates file
    return bool(save_json(SEED_ENTITY_CANDIDATES_PATH, list(items or [])))


def upsert_seed_entity_candidates(new_items: List[Dict[str, Any]]) -> Dict[str, int]:
    # upsert candidates by entity key
    existing = load_seed_entity_candidates()

    by_key: Dict[str, Dict[str, Any]] = {}
    for item in existing:
        # normalize item name
        name = normalize_entity_name(item.get("name"))
        k = entity_key(name)
        if not k:
            continue

        # normalize stored name
        item["name"] = name
        by_key[k] = item

    added = 0
    updated = 0

    # build update stamp
    stamp = datetime.now(timezone.utc).isoformat()

    for item in new_items or []:
        # validate item type
        if not isinstance(item, dict):
            continue

        # normalize input name
        name = normalize_entity_name(item.get("name"))
        if not name:
            continue

        # build lookup key
        k = entity_key(name)
        if not k:
            continue

        cur = by_key.get(k)
        if cur is None:
            # insert new candidate
            by_key[k] = dict(item)
            by_key[k]["name"] = name
            by_key[k]["last_seen_at"] = stamp
            added += 1
            continue

        # merge role list
        cur_roles = cur.get("roles")
        if not isinstance(cur_roles, list):
            cur_roles = []

        # include legacy role field
        old_role = normalize_spaces(str(cur.get("role") or ""))
        if old_role and old_role not in cur_roles:
            cur_roles.append(old_role)

        # include new role field
        new_role = normalize_spaces(str(item.get("role") or ""))
        if new_role and new_role not in cur_roles:
            cur_roles.append(new_role)

        # store role list
        cur["roles"] = cur_roles

        # update score
        old_score = float(cur.get("score", 0.0) or 0.0)
        new_score = float(item.get("score", 0.0) or 0.0)
        cur["score"] = float(round(max(old_score, new_score), 3))

        # update counters
        cur["mentions"] = int(max(int(cur.get("mentions", 0) or 0), int(item.get("mentions", 0) or 0)))
        cur["context_hits"] = int(max(int(cur.get("context_hits", 0) or 0), int(item.get("context_hits", 0) or 0)))

        # merge evidence list
        cur_ev = cur.get("evidence")
        if not isinstance(cur_ev, list):
            cur_ev = []

        cur_ev_map = set(_doc_evidence_key(e or {}) for e in cur_ev if isinstance(e, dict))

        in_ev = item.get("evidence")
        if isinstance(in_ev, list):
            for e in in_ev:
                # validate evidence type
                if not isinstance(e, dict):
                    continue

                # dedupe evidence
                ek = _doc_evidence_key(e)
                if ek in cur_ev_map:
                    continue

                # append evidence row
                cur_ev_map.add(ek)
                cur_ev.append(e)

        # store evidence list
        cur["evidence"] = cur_ev

        # update stamp
        cur["last_seen_at"] = stamp

        updated += 1

    # rebuild list
    merged = list(by_key.values())

    # sort by score desc
    merged.sort(key=lambda x: float(x.get("score", 0.0) or 0.0), reverse=True)

    # write file
    _ = save_seed_entity_candidates(merged)

    return {"added": int(added), "updated": int(updated), "total": int(len(merged))}


# ==================== PROMOTION ====================

def load_seed_entities_list() -> List[str]:
    # load seed entities list
    data = load_json(SEED_ENTITIES_PATH, default=[])
    if not isinstance(data, list):
        return []

    out: List[str] = []
    seen = set()

    for item in data:
        # validate item type
        if not isinstance(item, str):
            continue

        # normalize entity name
        s = normalize_entity_name(item)
        if not s:
            continue

        # dedupe name
        k = s.lower()
        if k in seen:
            continue

        seen.add(k)
        out.append(s)

    return out


def save_seed_entities_list(items: List[str]) -> bool:
    # save seed entities list
    return bool(save_json(SEED_ENTITIES_PATH, list(items or [])))


def promote_seed_entity_candidates() -> Dict[str, int]:
    # promote candidates into seed entities
    if not bool(SEED_EXPANSION_ENABLED):
        return {"promoted": 0, "candidates_total": 0, "seed_total": 0}

    # load candidate list
    candidates = load_seed_entity_candidates()

    # load seed list
    seed_entities = load_seed_entities_list()

    # build seed set
    seed_seen = set(s.lower() for s in seed_entities)

    # read promotion config
    promote_min = float(SEED_EXPANSION_PROMOTE_MIN_SCORE)
    cap = int(SEED_EXPANSION_MAX_PROMOTIONS_PER_RUN)
    if cap <= 0:
        cap = 20

    promoted = 0
    stamp = datetime.now(timezone.utc).isoformat()

    for item in candidates:
        # stop on cap
        if promoted >= cap:
            break

        # validate item type
        if not isinstance(item, dict):
            continue

        # normalize entity name
        name = normalize_entity_name(item.get("name"))
        if not name:
            continue

        # skip already promoted
        if item.get("promoted_at"):
            continue

        # read score value
        score = float(item.get("score", 0.0) or 0.0)
        if score < promote_min:
            continue

        low = name.lower()
        if low in seed_seen:
            # mark candidate promoted
            item["promoted_at"] = stamp
            continue

        # append into seed list
        seed_entities.append(name)
        seed_seen.add(low)

        # mark candidate promoted
        item["promoted_at"] = stamp
        promoted += 1

    # dedupe seed list
    seed_entities = list(dict.fromkeys(seed_entities))

    # write seed list
    _ = save_seed_entities_list(seed_entities)

    # write candidates list
    _ = save_seed_entity_candidates(candidates)

    return {
        "promoted": int(promoted),
        "candidates_total": int(len(candidates)),
        "seed_total": int(len(seed_entities)),
    }


# ==================== PUBLIC ====================

def record_seed_candidates_from_profile(query: str, profile: dict, documents: list) -> Dict[str, int]:
    # record profile candidates into file
    if not bool(SEED_EXPANSION_ENABLED):
        return {"added": 0, "updated": 0, "total": 0}

    # extract profile candidates
    items = extract_seed_candidates_from_profile(
        query=query,
        profile=profile,
        documents=documents,
    )

    # stop on empty items
    if not items:
        return {"added": 0, "updated": 0, "total": int(len(load_seed_entity_candidates()))}

    # upsert candidates list
    stats = upsert_seed_entity_candidates(items)

    return {
        "added": int(stats.get("added", 0)),
        "updated": int(stats.get("updated", 0)),
        "total": int(stats.get("total", 0)),
    }