"""
rerank search results by relevance
"""

import numpy as np
from typing import List, Dict, Any
from urllib.parse import urlparse

from haystack.core.component import component
from haystack.dataclasses import Document
from sentence_transformers import CrossEncoder


# ==================== RERANKER COMPONENT ====================

@component
class Reranker:

    def __init__(self, config):
        # store config reference
        self.config = config

        # load model settings
        self.model_name = config.RERANKER_MODEL
        self.max_length = config.RERANKER_MAX_LENGTH
        self.min_relevance = config.MIN_RELEVANCE_SCORE / 100.0
        self.top_k = config.TOP_K_RESULTS
        self.top_k_diverse = config.TOP_K_DIVERSE
        self.diversity_penalty = config.DIVERSITY_PENALTY

        # print status
        print(f"[RERANKER] Model: {self.model_name}")

        # load cross encoder model
        self.model = CrossEncoder(self.model_name, max_length=self.max_length)

    @component.output_types(documents=List[Document])
    def run(self, query: str, documents: List[Document]) -> Dict[str, Any]:
        # return empty if no documents
        if not documents:
            return {"documents": []}

        # read length caps
        min_len = self.config.RERANKER_MIN_DOC_LENGTH
        max_chars = self.config.RERANKER_MAX_DOC_CHARS

        valid = []
        for doc in documents:
            # normalize content
            text = (doc.content or "").strip()

            # skip short docs
            if len(text) < min_len:
                continue

            valid.append(doc)

        # stop on empty list
        if not valid:
            return {"documents": []}

        pairs = []
        for doc in valid:
            # clamp content size
            text = (doc.content or "")[:max_chars]

            # append query doc pair
            pairs.append([query, text])

        # run cross encoder prediction
        scores = self.model.predict(pairs, show_progress_bar=True)

        # normalize scores into 0..1
        normalized = 1 / (1 + np.exp(-scores))

        for i, doc in enumerate(valid):
            # assign score field
            doc.score = float(normalized[i])

        relevant = []
        for doc in valid:
            # filter by relevance threshold
            if doc.score >= self.min_relevance:
                relevant.append(doc)

        # stop on empty relevance list
        if not relevant:
            return {"documents": []}

        # compute filtered count
        filtered = len(valid) - len(relevant)
        if filtered > 0:
            print(f"[RERANKER] filtered {filtered} low-relevance docs")

        # sort by score desc
        ranked = sorted(relevant, key=lambda d: d.score, reverse=True)

        seen_domains = set()
        for doc in ranked[: self.top_k_diverse]:
            # read meta url
            meta = doc.meta or {}
            url = meta.get("url") or ""
            if not url:
                continue

            # normalize domain
            domain = urlparse(url).netloc.replace("www.", "")

            # apply diversity penalty
            if domain in seen_domains:
                doc.score *= self.diversity_penalty
            else:
                seen_domains.add(domain)

        # re-sort after penalty
        final_docs = sorted(ranked, key=lambda d: d.score, reverse=True)

        # clamp output size
        final_docs = final_docs[: self.top_k]

        # print output stats
        print(f"\n[RERANKER] returning {len(final_docs)} documents")
        return {"documents": final_docs}