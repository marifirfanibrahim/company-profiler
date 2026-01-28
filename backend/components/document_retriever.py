"""
retrieve documents from chromadb
"""

from typing import List, Dict, Any

from haystack.core.component import component
from haystack.dataclasses import Document


# ==================== DOCUMENT STORE RETRIEVER ====================

@component
class DocumentStoreRetriever:

    def __init__(self, config, document_store, embedder):
        # store config reference
        self.config = config

        # store dependencies
        self.document_store = document_store
        self.embedder = embedder

        # load settings from config
        self.top_k = config.DATABASE_RETRIEVAL_LIMIT

        if document_store:
            # print init status
            print(f"[DB_RETRIEVER] Initialized (top_k: {self.top_k})")

    @component.output_types(documents=List[Document])
    def run(self, query: str) -> Dict[str, Any]:
        # return empty if no store or embedder
        if not self.document_store or not self.embedder:
            return {"documents": []}

        # check document count in store
        doc_count = self.document_store.count_documents()
        if doc_count == 0:
            return {"documents": []}

        # encode query to embedding
        query_embedding = self.embedder.encode(query).tolist()

        # clamp top_k
        top_k = min(self.top_k, doc_count)

        # query chroma using low level api
        raw_results = self.document_store.query(
            query_embedding=query_embedding,
            top_k=top_k
        )

        documents: List[Document] = []

        # read content filter
        min_content_length = self.config.DATABASE_MIN_CONTENT_LENGTH

        for item in raw_results:
            # read content
            content = item.get("content") or ""
            content = content.strip()
            if not content or len(content) < min_content_length:
                continue

            # read meta
            meta_in = item.get("meta") or {}
            distance = float(item.get("distance", 1.0))

            # map distance to score
            score = 1.0 / (1.0 + max(distance, 0.0))

            # read stored fields
            url = meta_in.get("url", "#")
            title = meta_in.get("title", "Cached")
            snippet = meta_in.get("snippet") or content[: self.config.SNIPPET_LENGTH]
            stored_source = meta_in.get("source") or ""
            source_date = meta_in.get("source_date")

            # keep visible source label
            visible_source = stored_source if stored_source else "Database"

            # append document row
            documents.append(
                Document(
                    content=content,
                    meta={
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "source": visible_source,
                        "source_date": source_date,
                        "is_from_db": True,
                        "relevance_score": round(score, 3),
                    },
                )
            )

        if documents:
            # print result count
            print(f"[SOURCE] database: {len(documents)} cached results")
        else:
            # print empty status
            print(f"[SOURCE] database: 0 results after basic filters")

        return {"documents": documents}