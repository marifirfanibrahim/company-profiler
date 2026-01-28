"""
verify snapshot claims
select evidence by embeddings
run nli per claim
return checked snapshot
"""

import torch
from typing import List, Dict, Any
from urllib.parse import urlparse

from haystack.core.component import component
from haystack.core.serialization import default_from_dict, default_to_dict
from haystack.dataclasses import Document
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from backend.helpers.logic.fact_check_helpers import (
    split_snapshot_into_claims,
    build_evidence_texts,
    encode_texts,
    rank_evidence_by_embedding,
    build_evidence_rows,
    clamp01,
)


# ==================== FACT CHECKER COMPONENT ====================

@component
class FactChecker:


    # ------------------ INITIALIZATION ------------------

    def __init__(self, config):
        # store configuration objects
        self.config = config

        # load threshold from config
        self.threshold = config.FACT_CHECK_THRESHOLD

        # set model name from config
        self.model_name = config.FACT_CHECK_MODEL

        # print initialization message
        print(f"[FACT_CHECK] Model: {self.model_name}")

        # initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        # initialize model
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)

        # select device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # move model to device
        self.model = self.model.to(self.device)

        # set eval mode
        self.model.eval()

        # map label ids
        self.label_map = {"contradiction": 0, "neutral": 1, "entailment": 2}

        # print device label
        print(f"[FACT_CHECK] Device: {self.device}\n")


    # ------------------ SERIALIZATION ------------------

    def to_dict(self) -> Dict[str, Any]:
        # serialize component to dictionary
        return default_to_dict(self, config=self.config)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactChecker":
        # deserialize component from dictionary
        return default_from_dict(cls, data)


    # ------------------ WEBSITE NAME ------------------

    def _extract_website_name(self, url: str) -> str:
        # extract website label
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # drop www prefix
        if domain.startswith('www.'):
            domain = domain[4:]

        parts = domain.split('.')
        if len(parts) >= 2:
            # select domain token
            if parts[-2] in ['com', 'gov', 'org', 'net', 'co']:
                name = parts[0]
            else:
                name = parts[-2]

            # normalize separators
            name = name.replace('-', ' ').replace('_', ' ')
            return name.title()

        return domain

    def _build_citation_chain(self, source_name: str, is_from_db: bool, original_source: str, website_name: str) -> str:
        # build citation chain
        parts = []

        # add db marker
        if is_from_db:
            parts.append("Database")
            if original_source:
                parts.append(original_source)
        else:
            parts.append(source_name)

        # add website label
        if website_name:
            website_lower = website_name.lower().replace(' ', '')
            source_lower = source_name.lower().replace(' ', '')
            if website_lower not in source_lower and source_lower not in website_lower:
                parts.append(website_name)

        return " - ".join(parts)


    # ------------------ NLI ------------------

    def _nli_score(self, premise: str, hypothesis: str) -> Dict[str, float]:
        # run nli scoring
        inputs = self.tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(self.device)

        # run model forward
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)[0]

        # read class scores
        entail = float(probs[self.label_map["entailment"]].item())
        neutral = float(probs[self.label_map["neutral"]].item())
        contra = float(probs[self.label_map["contradiction"]].item())

        # compute support score
        neutral_weight = float(self.config.FACT_CHECK_NEUTRAL_WEIGHT)
        support = float(entail + (neutral * neutral_weight))
        support = float(clamp01(support))

        return {
            "support": support,
            "entailment": float(clamp01(entail)),
            "neutral": float(clamp01(neutral)),
            "contradiction": float(clamp01(contra)),
        }


    # ------------------ VERIFICATION ------------------

    @component.output_types(
        verified_snapshot=str,
        verified_claims=List[Dict[str, Any]],
        contradictions=List[Dict[str, Any]],
        fact_check_score=float,
    )
    def run(self, snapshot: str, documents: List[Document], embedder=None) -> Dict[str, Any]:
        # verify snapshot against documents
        snap = str(snapshot or "").strip()
        if not snap:
            return {
                "verified_snapshot": "",
                "verified_claims": [],
                "contradictions": [],
                "fact_check_score": 0.0,
            }

        # stop on missing docs
        if not documents:
            return {
                "verified_snapshot": snap,
                "verified_claims": [],
                "contradictions": [],
                "fact_check_score": float(self.threshold),
            }

        # stop on missing embedder
        if not embedder:
            return {
                "verified_snapshot": snap,
                "verified_claims": [],
                "contradictions": [],
                "fact_check_score": float(self.threshold),
            }

        # build claims
        max_claims = int(self.config.FACT_CHECK_MAX_CLAIMS)
        min_claim_length = int(self.config.FACT_CHECK_MIN_CLAIM_LENGTH)
        claims = split_snapshot_into_claims(
            snap,
            max_claims=max_claims,
            min_claim_length=min_claim_length,
        )
        if not claims:
            return {
                "verified_snapshot": snap,
                "verified_claims": [],
                "contradictions": [],
                "fact_check_score": float(self.threshold),
            }

        # build evidence texts
        max_premise = int(self.config.FACT_CHECK_PREMISE_MAX_CHARS)
        evidence_texts = build_evidence_texts(documents, max_chars=max_premise)

        # encode evidence vectors
        evidence_vecs = encode_texts(embedder, evidence_texts)

        # read settings
        top_k = int(self.config.FACT_CHECK_TOP_K_EVIDENCE)
        min_source_len = int(self.config.FACT_CHECK_MIN_SOURCE_LENGTH)
        contra_th = float(self.config.FACT_CHECK_CONTRADICTION_THRESHOLD)
        entail_max = float(self.config.FACT_CHECK_ENTAILMENT_MAX_FOR_CONTRADICTION)

        verified_claims: List[Dict[str, Any]] = []
        contradictions: List[Dict[str, Any]] = []
        accepted_scores: List[float] = []
        accepted_texts: List[str] = []

        for claim in claims:
            # encode claim vector
            claim_vecs = encode_texts(embedder, [claim])
            claim_vec = claim_vecs[0] if claim_vecs else []
            if not claim_vec:
                continue

            # rank evidence by similarity
            ranked = rank_evidence_by_embedding(
                claim_vec=claim_vec,
                evidence_vecs=evidence_vecs,
                top_k=top_k,
            )

            # map ranked indices
            evidence_rows = build_evidence_rows(documents, ranked)
            if not evidence_rows:
                continue

            claim_scores: List[float] = []
            claim_evidence: List[Dict[str, Any]] = []
            contradicted = False

            for row in evidence_rows:
                # read doc index
                doc_index = int(row.get("doc_index", 0))

                # read doc row
                doc = documents[doc_index]
                meta = doc.meta or {}

                # read premise text
                premise = str(doc.content or "").strip()
                if not premise or len(premise) < min_source_len:
                    continue

                # truncate premise
                if len(premise) > max_premise:
                    premise = premise[:max_premise]

                # compute nli scores
                scores = self._nli_score(premise=premise, hypothesis=claim)

                # read source labels
                source_name = str(meta.get("source", f"Source {doc_index + 1}") or "")
                source_url = str(meta.get("url", "#") or "")
                is_from_db = bool(meta.get("is_from_db"))
                original_source = meta.get("original_source")

                # compute website label
                website_name = meta.get("website_name") or self._extract_website_name(source_url)

                # build citation chain
                source_chain = self._build_citation_chain(source_name, is_from_db, original_source, website_name)

                # append evidence item
                claim_evidence.append(
                    {
                        "doc_index": doc_index,
                        "title": str(meta.get("title", "Unknown") or ""),
                        "url": source_url,
                        "source": source_chain,
                        "source_date": meta.get("source_date"),
                        "similarity": float(row.get("similarity", 0.0)),
                        "support_score": float(round(scores["support"], 3)),
                        "contradiction_score": float(round(scores["contradiction"], 3)),
                        "entailment_score": float(round(scores["entailment"], 3)),
                        "neutral_score": float(round(scores["neutral"], 3)),
                    }
                )

                # contradiction rule
                if scores["contradiction"] >= contra_th and scores["entailment"] <= entail_max:
                    contradicted = True
                    contradictions.append(
                        {
                            "claim": claim,
                            "evidence": {
                                "doc_index": doc_index,
                                "title": str(meta.get("title", "Unknown") or ""),
                                "url": source_url,
                                "source": source_chain,
                                "source_date": meta.get("source_date"),
                                "similarity": float(row.get("similarity", 0.0)),
                            },
                        }
                    )
                    break

                # store support scores
                claim_scores.append(float(scores["support"]))

            # skip contradicted claim
            if contradicted:
                continue

            # skip empty score list
            if not claim_scores:
                continue

            # compute avg claim score
            avg = sum(claim_scores) / float(len(claim_scores))
            avg = float(clamp01(avg))

            # append verified claim
            verified_claims.append(
                {
                    "claim": claim,
                    "confidence": float(round(avg, 3)),
                    "evidence": claim_evidence,
                }
            )

            # store accepted claim
            accepted_scores.append(avg)
            accepted_texts.append(claim)

        # compute overall fact check score
        if accepted_scores:
            fc_score = sum(accepted_scores) / float(len(accepted_scores))
            fc_score = float(clamp01(fc_score))
        else:
            fc_score = float(self.threshold)

        # build verified snapshot
        verified_snapshot = " ".join([c.strip() for c in accepted_texts if c and c.strip()]).strip()
        if not verified_snapshot:
            verified_snapshot = snap

        # print stats
        print(f"[FACT_CHECK] claims total: {len(claims)}")
        print(f"[FACT_CHECK] claims accepted: {len(accepted_texts)}")
        print(f"[FACT_CHECK] claims contradicted: {len(contradictions)}")
        print(f"[FACT_CHECK] fact check score: {fc_score:.3f}")

        return {
            "verified_snapshot": verified_snapshot,
            "verified_claims": verified_claims,
            "contradictions": contradictions,
            "fact_check_score": float(fc_score),
        }