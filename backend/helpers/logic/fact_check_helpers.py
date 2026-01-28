"""
split snapshot claims
encode evidence chunks
rank evidence by similarity
"""

import re
import math
from typing import List, Dict, Any, Tuple


# ============== CLAIMS ==============

def split_snapshot_into_claims(text: str, max_claims: int, min_claim_length: int) -> List[str]:
    # normalize input text
    s = str(text or "").strip()
    if not s:
        return []

    # normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # split sentence boundaries
    parts = re.split(r"(?<=[\.\?\!])\s+", s)

    claims: List[str] = []
    for part in parts:
        # normalize claim
        c = str(part or "").strip()
        if not c:
            continue

        # skip short fragments
        if int(min_claim_length) > 0 and len(c) < int(min_claim_length):
            continue

        # append claim
        claims.append(c)

        # enforce cap
        if int(max_claims) > 0 and len(claims) >= int(max_claims):
            break

    return claims


# ============== TEXTS ==============

def build_evidence_texts(documents: list, max_chars: int) -> List[str]:
    # build truncated evidence texts
    texts: List[str] = []

    for doc in documents or []:
        # read doc content
        raw = str(getattr(doc, "content", "") or "").strip()
        if not raw:
            texts.append("")
            continue

        # truncate text
        if int(max_chars) > 0 and len(raw) > int(max_chars):
            raw = raw[: int(max_chars)]

        # normalize spaces
        raw = re.sub(r"\s+", " ", raw).strip()
        texts.append(raw)

    return texts


# ============== VECTORS ==============

def encode_texts(embedder, texts: List[str]) -> List[List[float]]:
    # encode texts into float vectors
    if not embedder:
        return []

    # normalize list input
    items = list(texts or [])
    if not items:
        return []

    # encode using embedder
    vecs = embedder.encode(items)
    if hasattr(vecs, "tolist"):
        vecs = vecs.tolist()

    out: List[List[float]] = []
    for v in vecs or []:
        # normalize vector row
        out.append(list(v) if isinstance(v, list) else [])

    return out


def cosine_similarity(a: List[float], b: List[float]) -> float:
    # compute cosine similarity
    if not a or not b:
        return 0.0

    # require equal sizes
    if len(a) != len(b):
        return 0.0

    dot = 0.0
    na = 0.0
    nb = 0.0

    for i in range(len(a)):
        # read elements
        av = float(a[i])
        bv = float(b[i])

        # accumulate dot and norms
        dot += av * bv
        na += av * av
        nb += bv * bv

    # avoid division by zero
    if na <= 0.0 or nb <= 0.0:
        return 0.0

    return float(dot / (math.sqrt(na) * math.sqrt(nb)))


def clamp01(x: float) -> float:
    # clamp into 0..1
    v = float(x)
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


# ============== EVIDENCE ==============

def rank_evidence_by_embedding(
    claim_vec: List[float],
    evidence_vecs: List[List[float]],
    top_k: int,
) -> List[Tuple[int, float]]:
    # return ranked evidence indices
    ranked: List[Tuple[int, float]] = []

    # validate inputs
    if not claim_vec or not evidence_vecs:
        return []

    # compute all similarities
    for idx, vec in enumerate(evidence_vecs):
        sim = cosine_similarity(claim_vec, vec)
        ranked.append((int(idx), float(sim)))

    # sort by similarity
    ranked.sort(key=lambda x: float(x[1]), reverse=True)

    # cap output
    k = int(top_k)
    if k <= 0:
        return ranked

    return ranked[:k]


def build_evidence_rows(
    documents: list,
    ranked_indices: List[Tuple[int, float]],
) -> List[Dict[str, Any]]:
    # map ranked indices to evidence rows
    rows: List[Dict[str, Any]] = []

    for idx, sim in ranked_indices or []:
        # validate index
        if idx < 0 or idx >= len(documents):
            continue

        # read meta
        doc = documents[idx]
        meta = getattr(doc, "meta", None) or {}

        # append row
        rows.append(
            {
                "doc_index": int(idx),
                "similarity": float(sim),
                "title": str(meta.get("title", "") or ""),
                "url": str(meta.get("url", "") or ""),
                "source": str(meta.get("source", "") or ""),
                "source_date": meta.get("source_date"),
                "is_from_db": bool(meta.get("is_from_db")),
                "original_source": meta.get("original_source"),
            }
        )

    return rows