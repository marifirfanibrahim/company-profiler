"""
api search routes
orchestrate the search workflow using the main haystack pipeline
handle search requests and return results
"""

import time
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone

from backend.helpers.persist.store_helpers import clamp_profile_documents


# create search blueprint
search_bp = Blueprint("search", __name__)


# ==================== ORCHESTRATOR ====================

@search_bp.route("/search", methods=["POST"])
def search():
    # record start time
    start_time = time.time()

    # retrieve components from flask app context
    components = current_app.components
    rag_pipeline = components.get("pipeline")
    profiles_db = components.get("profiles_db")
    doc_store = components.get("doc_store")
    config = components.get("config")

    # read request json
    json_data = request.get_json()
    if not isinstance(json_data, dict):
        return jsonify({"error": "invalid json payload"}), 400

    # read query fields
    query = str(json_data.get("query", "") or "").strip()
    model_id = json_data.get("model_id") or None

    # validate required query
    if not query:
        return jsonify({"error": "Query is required"}), 400

    # validate pipeline presence
    if not rag_pipeline:
        return jsonify({"error": "Search pipeline not initialized"}), 503

    # log search start
    model_msg = f" | Model: {model_id}" if model_id else ""
    now_iso = datetime.now().isoformat()
    print(
        f"\n{'=' * 70}\n"
        f"SEARCH: {query}\n"
        f"Time: {now_iso}{model_msg}\n"
        f"{'=' * 70}\n"
    )

    # run pipeline
    pipeline_result = rag_pipeline.run(
        query=query,
        model_id=model_id,
    )

    # extract fields
    snapshot = pipeline_result.get("snapshot", "") or ""
    customer = pipeline_result.get("customer") or {}
    corporate_guarantor = pipeline_result.get("corporate_guarantor") or {}
    high_risk_entities = pipeline_result.get("high_risk_entities") or []

    # check output presence
    has_profile_data = bool(
        (snapshot and snapshot.strip())
        or customer
        or corporate_guarantor
        or high_risk_entities
    )

    if not has_profile_data:
        print("\n→ No profile generated")
        return jsonify(
            {
                "query": query,
                "snapshot": "",
                "customer": {},
                "corporate_guarantor": {},
                "high_risk_entities": [],
                "confidence_score": 0.0,
                "documents": [],
                "error": "No relevant profile information found or snapshot could not be generated.",
            }
        ), 200

    # compute response timing
    search_time = round(time.time() - start_time, 2)
    timestamp_iso = datetime.now().isoformat()

    # build response
    response = {
        "query": query,
        "search_time": search_time,
        "timestamp": timestamp_iso,
        **pipeline_result,
    }

    # init profile id
    profile_id = None

    # build stored docs
    stored_documents = clamp_profile_documents(
        config=config,
        documents=response.get("documents") or [],
    )

    # save profile
    if profiles_db:
        profile_id = profiles_db.save_profile(
            company=query,
            snapshot=response.get("snapshot", "") or "",
            customer=response.get("customer") or {},
            corporate_guarantor=response.get("corporate_guarantor") or {},
            high_risk_entities=response.get("high_risk_entities") or [],
            documents=stored_documents,
            confidence=response.get("confidence_score", 0.0),
            created_at=timestamp_iso,
        )
        print(f"[SEARCH] saved profile id {profile_id} for '{query}'")

    # attach profile id
    response["profile_id"] = profile_id

    # optional indexing into chroma
    if config and config.ENABLE_DB_INDEXING:
        # read embedder
        embedder = rag_pipeline.embedder

        if embedder and doc_store and hasattr(doc_store, "add_documents"):
            # load indexing settings
            min_len = config.DATABASE_MIN_CONTENT_LENGTH
            max_docs = config.DATABASE_MAX_INDEX_DOCS
            truncate_len = config.DATABASE_INDEX_TRUNCATE_LENGTH

            # build payload arrays
            texts = []
            metas = []

            # build indexed stamp
            date_fmt = config.DATE_STAMP_FORMAT
            indexed_at = datetime.now(timezone.utc).strftime(date_fmt)
            profile_conf = float(response.get("confidence_score", 0.0) or 0.0)

            for doc_dict in response.get("documents", []):
                # read meta
                meta = doc_dict.get("meta", {}) or {}
                if meta.get("is_from_db"):
                    continue

                # read content
                content = doc_dict.get("content", "")
                if not content or len(content) < min_len:
                    continue

                # apply truncate
                if truncate_len and truncate_len > 0:
                    truncated = content[:truncate_len]
                else:
                    truncated = content

                # update meta fields
                meta["indexed_at"] = indexed_at
                meta["profile_id"] = profile_id
                meta["profile_confidence"] = profile_conf
                meta["indexed_reason"] = "live_search"

                # store row
                texts.append(truncated)
                metas.append(meta)

                # enforce cap
                if len(texts) >= max_docs:
                    break

            if texts:
                # encode embeddings
                embeddings = embedder.encode(texts)
                if hasattr(embeddings, "tolist"):
                    embeddings = embeddings.tolist()

                # build chroma docs
                docs_to_index = []
                for i, text in enumerate(texts):
                    # append payload
                    docs_to_index.append(
                        {
                            "content": text,
                            "meta": metas[i],
                            "embedding": embeddings[i],
                        }
                    )

                print(f"[SEARCH] indexing {len(docs_to_index)} documents into chromadb")
                doc_store.add_documents(docs_to_index)

    print(
        f"\n{'=' * 70}\n"
        f"COMPLETE | Duration: {search_time:.1f}s | Confidence: {response['confidence_score']:.2f}\n"
        f"{'=' * 70}\n"
    )

    # return json response
    return jsonify(response)