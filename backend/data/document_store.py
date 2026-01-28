"""
manage chromadb document store for haystack
initialize and configure vector storage
provide persistence for documents
"""

from typing import List, Dict, Any
from pathlib import Path

from haystack.dataclasses import Document
from haystack_integrations.document_stores.chroma import ChromaDocumentStore

from backend.configuration.paths import CHROMA_DB_PATH, STORES_DIR
from backend.helpers.persist.store_helpers import sanitize_meta


# ==================== BASE CHROMA STORE ====================

class BaseChromaDocumentStore(ChromaDocumentStore):


    # ------------------ INITIALIZATION ------------------

    def __init__(self, persist_path: Path, collection_name: str):
        # store collection id
        self.collection_name = collection_name

        # ensure directory exists
        path = Path(persist_path)
        path.mkdir(parents=True, exist_ok=True)

        # init base store
        super().__init__(
            persist_path=str(path),
            collection_name=collection_name
        )

        # ensure internal client init
        if hasattr(self, "_ensure_initialized"):
            # call internal initializer
            self._ensure_initialized()

            # touch client handles
            _ = self._client
            _ = self._collection


    # ------------------ QUERY HELPERS ------------------

    def query(self, query_embedding: List[float], top_k: int) -> List[Dict[str, Any]]:
        # query chroma collection and return raw dicts
        if not query_embedding:
            return []

        # read collection handle
        collection = self._collection

        # run chroma query
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(1, top_k),
            include=["documents", "metadatas", "distances"]
        )

        # read chroma arrays
        docs_list = (result.get("documents") or [[]])[0]
        metas_list = (result.get("metadatas") or [[]])[0]
        dists_list = (result.get("distances") or [[]])[0]

        out: List[Dict[str, Any]] = []
        for idx, content in enumerate(docs_list):
            # read meta and distance
            meta_raw = metas_list[idx] if idx < len(metas_list) else {}
            dist = dists_list[idx] if idx < len(dists_list) else 1.0

            # append normalized row
            out.append({
                "content": content,
                "meta": sanitize_meta(meta_raw),
                "distance": float(dist)
            })

        return out


# ==================== PRIMARY STORE ====================

class BZChromaDocumentStore(BaseChromaDocumentStore):


    # ------------------ INITIALIZATION ------------------

    def __init__(self, config=None):
        # store config reference
        self.config = config

        # define base path
        chroma_path = CHROMA_DB_PATH

        # read collection name
        collection_name = config.CHROMA_COLLECTION_NAME

        # init base store
        super().__init__(persist_path=chroma_path, collection_name=collection_name)

        # log status
        print(f"[DOCSTORE] connected to: {chroma_path} (collection: {self.collection_name})")


    # ------------------ WRITE API ------------------

    def add_documents(self, docs: List[Dict[str, Any]]):
        # add docs with embeddings into primary store
        if not docs:
            return

        hs_docs: List[Document] = []

        for item in docs:
            # read doc fields
            content = item.get("content") or ""
            embedding = item.get("embedding")
            meta_in = item.get("meta") or {}

            # skip empty content
            if not content:
                continue

            # sanitize meta
            meta = sanitize_meta(meta_in)

            # append haystack doc
            hs_docs.append(
                Document(
                    content=content,
                    meta=meta,
                    embedding=embedding
                )
            )

        # stop on empty payload
        if not hs_docs:
            return

        # write docs into store
        self.write_documents(hs_docs)

        # print status
        print(f"[DOCSTORE] added {len(hs_docs)} documents to chroma")


# ==================== READ ONLY STORE ====================

class ReadOnlyChromaStore(BaseChromaDocumentStore):


    # ------------------ INITIALIZATION ------------------

    def __init__(self, path: Path, collection_name: str):
        # init read only store for external folder
        super().__init__(persist_path=path, collection_name=collection_name)
        print(f"[DOCSTORE] attached external chroma folder: {path} (collection: {self.collection_name})")


    # ------------------ WRITE BLOCK ------------------

    def add_documents(self, docs: List[Dict[str, Any]]):
        # disable writes for external stores
        return


# ==================== MULTI STORE AGGREGATOR ====================

class MultiChromaDocumentStore:


    # ------------------ INITIALIZATION ------------------

    def __init__(self, config=None):
        # store config reference
        self.config = config

        # build primary store
        self.primary_store = BZChromaDocumentStore(config=config)

        # build list of stores
        self.stores: List[BaseChromaDocumentStore] = [self.primary_store]

        # attach extra folders
        self._attach_external_stores()

    def _attach_external_stores(self):
        # attach extra chroma stores found in stores directory
        root = STORES_DIR
        base_path = CHROMA_DB_PATH.resolve()

        # stop on missing folder
        if not root.exists():
            return

        # scan folder children
        for child in root.iterdir():
            # skip non directories
            if not child.is_dir():
                continue

            # skip primary folder
            if child.resolve() == base_path:
                continue

            # check for chroma sqlite file
            sql_file = child / "chroma.sqlite3"
            if not sql_file.exists():
                continue

            # attach read only store
            store = ReadOnlyChromaStore(
                path=child,
                collection_name=self.config.CHROMA_COLLECTION_NAME
            )
            self.stores.append(store)

        # print store status
        total = len(self.stores)
        if total > 1:
            print(f"[DOCSTORE] multi store active with {total} folders")
        else:
            print("[DOCSTORE] single chroma folder only")


    # ------------------ WRITE API ------------------

    def add_documents(self, docs: List[Dict[str, Any]]):
        # add docs only to primary store
        if not docs:
            return

        # forward to primary store
        self.primary_store.add_documents(docs)


    # ------------------ READ API ------------------

    def count_documents(self) -> int:
        # count docs across all stores
        total = 0
        for store in self.stores:
            # read store count
            count = store.count_documents()
            if isinstance(count, int):
                total += count
        return total

    def query(self, query_embedding: List[float], top_k: int) -> List[Dict[str, Any]]:
        # query all stores and merge results
        if not query_embedding:
            return []

        all_hits: List[Dict[str, Any]] = []

        for store in self.stores:
            # query each store
            hits = store.query(query_embedding=query_embedding, top_k=top_k)
            if not hits:
                continue

            # append hits
            for item in hits:
                all_hits.append(item)

        # stop on empty
        if not all_hits:
            return []

        # dedupe by url and content hash
        merged: List[Dict[str, Any]] = []
        seen_keys = set()

        for item in all_hits:
            # normalize content
            content = str(item.get("content") or "").strip()

            # read meta url
            meta = item.get("meta") or {}
            url = str(meta.get("url") or "").strip()

            # build dedupe key
            key = f"{url}|{hash(content)}"
            if key in seen_keys:
                continue

            # store key and row
            seen_keys.add(key)
            merged.append(item)

        # sort by distance
        merged_sorted = sorted(
            merged,
            key=lambda x: float(x.get("distance", 1.0))
        )

        return merged_sorted[:top_k]


# ==================== FACTORY FUNCTION ====================

def get_document_store(config):
    # build multi chroma store aggregator
    return MultiChromaDocumentStore(config=config)