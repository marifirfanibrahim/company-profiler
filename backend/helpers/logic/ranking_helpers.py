"""
prefer newer documents
penalize low confidence cache
apply ranking adjustments
"""

import math
from datetime import datetime, timezone
from typing import List

from backend.helpers.parse.date_helpers import parse_yyyy_mm_dd_datetime


# ============== DATE PARSE ==============

def get_best_doc_date(meta: dict) -> datetime:
    # select best date from meta
    m = meta or {}

    # prefer source date
    dt = parse_yyyy_mm_dd_datetime(m.get("source_date"))
    if dt:
        return dt

    # fallback to indexed date
    dt = parse_yyyy_mm_dd_datetime(m.get("indexed_at"))
    if dt:
        return dt

    return None


# ============== SCORE ==============

def clamp01(x: float) -> float:
    # clamp into 0..1
    v = float(x)
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def recency_decay(age_days: int, half_life_days: int) -> float:
    # compute exp decay value
    hl = int(half_life_days)
    if hl < 1:
        hl = 1

    a = int(age_days)
    if a < 0:
        a = 0

    return float(math.exp(-float(a) / float(hl)))


def apply_recency_and_cache_quality(config, documents: List):
    # adjust document scores then sort
    if not documents:
        return []

    # read config
    prefer_newer = bool(getattr(config, "PIPELINE_PREFER_NEWER"))
    recency_weight = float(getattr(config, "PIPELINE_RECENCY_WEIGHT"))
    half_life = int(getattr(config, "PIPELINE_RECENCY_HALF_LIFE_DAYS"))
    cache_weight = float(getattr(config, "PIPELINE_CACHE_CONFIDENCE_WEIGHT"))

    # build now time
    now = datetime.now(timezone.utc)

    for doc in documents:
        # read meta
        meta = getattr(doc, "meta", None) or {}

        # read base score
        base = 0.0
        if getattr(doc, "score", None) is not None:
            base = float(doc.score or 0.0)
        elif meta.get("relevance_score") is not None:
            base = float(meta.get("relevance_score") or 0.0)

        # init bonus value
        bonus = 0.0

        # add recency bonus
        if prefer_newer:
            dt = get_best_doc_date(meta)
            if dt:
                # compute age in days
                age_days = int((now - dt).days)

                # compute recency factor
                rf = recency_decay(age_days=age_days, half_life_days=half_life)

                # apply weight
                bonus = float(recency_weight * rf)

        # init multiplier value
        mult = 1.0

        # apply cache confidence multiplier
        if meta.get("profile_confidence") is not None:
            # clamp confidence
            pc = clamp01(float(meta.get("profile_confidence") or 0.0))

            # compute weighted multiplier
            mult = float((1.0 - cache_weight) + (cache_weight * pc))

        # write score back
        doc.score = float((base + bonus) * mult)

    # sort docs by adjusted score
    return sorted(
        documents,
        key=lambda d: float(getattr(d, "score", 0.0) or 0.0),
        reverse=True
    )