"""
summarization helpers
run snapshot and profile
"""

import time

from backend.helpers.logic.ranking_helpers import apply_recency_and_cache_quality
from backend.helpers.logic.pipeline_helpers import (
    prefer_documents_by_query_phrase,
    filter_high_risk_entities,
    prefer_documents_by_profile_names,
)
from backend.configuration.seeding import SEED_EXPANSION_ENABLED
from backend.helpers.logic.seed_helpers import record_seed_candidates_from_profile


# ==================== SUMMARIZATION MIXIN ====================

class SummarizationMixin:

    def _summarize_from_documents(self, query: str, llm, all_documents: list):
        # run snapshot and profile pipeline
        step_times = {}

        # select top candidates
        print("[PIPELINE] selecting documents...")
        t_pre = time.time()

        # copy input list
        top_candidates = list(all_documents)

        # compute initial cap
        max_initial = int(self.config.SUMMARIZATION_MAX_DOCS) * 3

        # clamp candidate list
        if len(top_candidates) > max_initial:
            top_candidates = top_candidates[:max_initial]

        # store timing
        step_times["pre_ranking"] = time.time() - t_pre

        if not top_candidates:
            # stop on empty list
            print("[PIPELINE] no documents available for summarization")
            return None

        print(f"[PIPELINE] Top candidates: {len(top_candidates)}")

        # content extraction
        print("[PIPELINE] Extracting content...")
        t_ce = time.time()

        # read fetch flag
        fetch_enabled = bool(self.config.PIPELINE_CONTENT_FETCH_ENABLED)
        if fetch_enabled:
            # run extractor component
            content_extractor = self.components["content_extractor"]
            extracted_result = content_extractor.run(documents=top_candidates)
            extracted_docs = extracted_result.get("documents", [])
        else:
            # keep original docs
            extracted_docs = list(top_candidates)

        # store timing
        step_times["content_extraction"] = time.time() - t_ce

        if not extracted_docs:
            # stop on empty extraction result
            print("[PIPELINE] No documents after extraction")
            return None

        # drop empty docs
        non_empty_docs = []
        for d in extracted_docs:
            # keep only docs with content
            content = str(getattr(d, "content", "") or "").strip()
            if not content:
                continue
            non_empty_docs.append(d)

        if not non_empty_docs:
            # stop on empty list
            print("[PIPELINE] No documents after empty drop")
            return None

        # store filtered docs
        extracted_docs = non_empty_docs

        print(f"[PIPELINE] After extraction: {len(extracted_docs)} documents")

        # cleaning
        print("[PIPELINE] Cleaning documents...")
        t_clean = time.time()

        # run cleaner
        document_cleaner = self.components["document_cleaner"]
        cleaned_result = document_cleaner.run(documents=extracted_docs)

        # store timing
        step_times["cleaning"] = time.time() - t_clean

        # read cleaned docs
        cleaned_docs = cleaned_result.get("documents", [])

        if not cleaned_docs:
            # stop on empty list
            print("[PIPELINE] No documents after cleaning")
            return None

        # rerank documents before splitting
        reranker = self.components.get("reranker")
        enable_reranking = bool(self.config.PIPELINE_ENABLE_RERANKING) and bool(reranker)

        # set doc list for splitting
        docs_for_split = cleaned_docs

        if enable_reranking:
            # start rerank timer
            print("[PIPELINE] Reranking documents before splitting...")
            t_rr_docs = time.time()

            # run reranker
            rr_result = reranker.run(query=query, documents=cleaned_docs)

            # store timing
            step_times["rerank_docs"] = time.time() - t_rr_docs

            # read docs
            rr_docs = rr_result.get("documents", []) if isinstance(rr_result, dict) else []

            # apply recency and cache
            rr_docs = apply_recency_and_cache_quality(self.config, rr_docs)

            # read selection cap
            top_n = int(self.config.PIPELINE_RERANK_TOP_DOCS)

            if rr_docs:
                # keep reranked docs
                docs_for_split = rr_docs[:top_n]
                print(f"[PIPELINE] Using top {len(docs_for_split)} reranked documents for splitting")
            else:
                # fallback to cleaned docs
                docs_for_split = cleaned_docs[:top_n]
                print(f"[PIPELINE] Using top {len(docs_for_split)} documents for splitting (reranker returned empty)")

        # store docs for sources
        docs_for_sources = list(docs_for_split)

        # splitting
        print("[PIPELINE] Splitting documents...")
        t_split = time.time()

        # run splitter
        document_splitter = self.components["document_splitter"]
        split_result = document_splitter.run(documents=docs_for_split)

        # store timing
        step_times["splitting"] = time.time() - t_split

        # read split docs
        split_docs = split_result.get("documents", [])

        if not split_docs:
            # stop on empty chunk list
            print("[PIPELINE] No documents after splitting")
            return None

        print(f"[PIPELINE] After splitting: {len(split_docs)} chunks")

        # phrase filter
        phrase_docs = prefer_documents_by_query_phrase(self.config, query, split_docs)

        # print phrase stats
        if phrase_docs and len(phrase_docs) != len(split_docs):
            print(f"[PIPELINE] phrase filter: {len(phrase_docs)}/{len(split_docs)} chunks matched")
        else:
            print(f"[PIPELINE] phrase filter: {len(phrase_docs)}/{len(split_docs)} chunks used")

        # selection
        max_docs = int(self.config.SUMMARIZATION_MAX_DOCS)
        selected_docs = phrase_docs[:max_docs]

        # rerank chunks for final selection
        if enable_reranking and bool(self.config.PIPELINE_RERANK_CHUNKS):
            # start chunk rerank timer
            print("[PIPELINE] Reranking chunks for final selection...")
            t_rr_chunks = time.time()

            # read chunk candidate cap
            max_candidates = int(self.config.PIPELINE_RERANK_CHUNK_CANDIDATES)

            # clamp candidates
            candidates = phrase_docs[:max_candidates] if len(phrase_docs) > max_candidates else phrase_docs

            # run reranker
            rr_chunk_result = reranker.run(query=query, documents=candidates)

            # store timing
            step_times["rerank_chunks"] = time.time() - t_rr_chunks

            # read docs
            rr_chunks = rr_chunk_result.get("documents", []) if isinstance(rr_chunk_result, dict) else []

            # apply recency and cache
            rr_chunks = apply_recency_and_cache_quality(self.config, rr_chunks)

            if rr_chunks:
                # keep reranked chunks
                selected_docs = rr_chunks[:max_docs]
                print(f"[PIPELINE] Using top {len(selected_docs)} reranked chunks for profile extraction")
            else:
                # fallback to candidates
                selected_docs = candidates[:max_docs]
                print(f"[PIPELINE] Using top {len(selected_docs)} chunks for profile extraction (reranker returned empty)")
        else:
            # start selection timer
            print("[PIPELINE] Selecting documents without reranker...")
            t_final = time.time()

            # apply recency and cache
            phrase_docs = apply_recency_and_cache_quality(self.config, phrase_docs)
            selected_docs = phrase_docs[:max_docs]

            # store timing
            step_times["document_selection"] = time.time() - t_final
            print(f"[PIPELINE] Using top {len(selected_docs)} documents for profile extraction")

        if not selected_docs:
            # stop on empty selection
            print("[PIPELINE] no documents selected after splitting")
            return None

        # snapshot generation
        print("[PIPELINE] Generating snapshot...")
        t_snap = time.time()

        # read component
        snapshot_extractor = self.components.get("snapshot_extractor")

        # run snapshot model
        if snapshot_extractor:
            snapshot = snapshot_extractor.run(
                company=query,
                documents=selected_docs,
                llm=llm,
            )
        else:
            snapshot = ""

        # store timing
        step_times["snapshot_generation"] = time.time() - t_snap

        # fact checking
        print("[PIPELINE] Fact checking snapshot...")
        t_fc = time.time()

        # init values
        fact_check_score = None
        fact_check_details = None

        # read checker component
        fact_checker = self.components.get("fact_checker")

        # run fact checker
        if bool(self.config.ENABLE_FACT_CHECKING) and fact_checker and snapshot:
            fc_result = fact_checker.run(
                snapshot=snapshot,
                documents=selected_docs,
                embedder=self.embedder,
            )

            # apply verified snapshot
            verified = fc_result.get("verified_snapshot")
            if isinstance(verified, str) and verified.strip():
                snapshot = verified

            # store scores and details
            fact_check_score = fc_result.get("fact_check_score")
            fact_check_details = {
                "verified_claims": fc_result.get("verified_claims") or [],
                "contradictions": fc_result.get("contradictions") or [],
            }

        # store timing
        step_times["fact_checking"] = time.time() - t_fc

        # entity and relationship extraction
        print("[PIPELINE] Extracting entities and relationships for context...")
        t_ent = time.time()

        # init lists
        entities = []
        relationships = []

        # build ner text
        text_for_ner = self._build_text_for_entities(selected_docs)

        # run entity extractor
        entity_extractor = self.components.get("entity_extractor")
        if bool(self.config.ENABLE_ENTITY_EXTRACTION) and entity_extractor and text_for_ner:
            ent_result = entity_extractor.run(text=text_for_ner)
            entities = ent_result.get("entities", []) or []

        # run relationship extractor
        relationship_extractor = self.components.get("relationship_extractor")
        if bool(self.config.ENABLE_RELATIONSHIPS) and relationship_extractor and entities and text_for_ner:
            rel_result = relationship_extractor.run(
                text=text_for_ner,
                entities=entities,
            )
            relationships = rel_result.get("relationships", []) or []

        # store timing
        step_times["entity_relationship_extraction"] = time.time() - t_ent

        # profile extraction
        print("[PIPELINE] Extracting structured profile...")
        t_prof = time.time()

        # read component
        profile_extractor = self.components.get("profile_extractor")

        # run profile model
        if profile_extractor:
            profile = profile_extractor.run(
                company=query,
                documents=selected_docs,
                llm=llm,
                entities=entities,
                relationships=relationships,
            )
        else:
            profile = {
                "customer": {},
                "corporate_guarantor": {},
                "high_risk_entities": [],
            }

        # apply high risk filter
        profile = filter_high_risk_entities(self.config, query, profile)

        # record candidates for seeding
        if bool(SEED_EXPANSION_ENABLED):
            stats = record_seed_candidates_from_profile(
                query=query,
                profile=profile,
                documents=selected_docs,
            )
            if int(stats.get("added", 0)) or int(stats.get("updated", 0)):
                print(
                    "[SEED_EXPANSION] "
                    f"candidates added={stats.get('added', 0)}, "
                    f"updated={stats.get('updated', 0)}, "
                    f"total={stats.get('total', 0)}"
                )

        # store timing
        step_times["profile_extraction"] = time.time() - t_prof

        # reorder docs for sources by profile names
        docs_for_sources = prefer_documents_by_profile_names(profile, docs_for_sources)

        # format final output
        output = self._format_output(
            documents=docs_for_sources,
            snapshot=snapshot,
            profile=profile,
            fact_check_score=fact_check_score,
            fact_check_details=fact_check_details,
        )

        return {
            "output": output,
            "timings": step_times,
        }

    def _build_text_for_entities(self, documents: list) -> str:
        # build concatenated text for entity extraction
        if not documents:
            return ""

        # read cap
        max_chars = int(self.config.PROFILE_ENTITY_MAX_TEXT_CHARS)

        chunks: list = []
        total = 0

        for doc in documents:
            # read doc content
            content = (doc.content or "").strip()
            if not content:
                continue

            # compute remaining budget
            remaining = max_chars - total
            if remaining <= 0:
                break

            # append limited content
            piece = content[:remaining]
            chunks.append(piece)
            total += len(piece)

        # join text
        return " ".join(chunks).strip()