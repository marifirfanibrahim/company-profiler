"""
main haystack pipeline
orchestrate search flow
manage model routing
"""

import time
from haystack.components.preprocessors import DocumentSplitter, DocumentCleaner

from .retrieval import RetrievalMixin
from .summarization import SummarizationMixin
from .output import OutputMixin

from backend.helpers.logic.helper import apply_hf_hub_env


# ==================== RAG PIPELINE ====================

class Pipeline(RetrievalMixin, SummarizationMixin, OutputMixin):

    def __init__(self, config, document_store):
        # store references
        self.config = config
        self.document_store = document_store

        # set hf hub env
        apply_hf_hub_env(self.config)

        # initialize embedder
        self.embedder = self._init_embedder()

        # store retriever ids
        self.retriever_names = []

        # store component refs
        self.components = {}

        # store generator refs
        self.current_generator = None
        self.current_model_id = None

        # build component registry
        self._build_pipeline()

        # warm up components
        self._warm_up_components()

    def _init_embedder(self):
        # import sentence model
        from sentence_transformers import SentenceTransformer

        # build embedder instance
        embedder = SentenceTransformer(self.config.EMBEDDER_MODEL)

        # print model id
        print(f"[PIPELINE] Embedder: {self.config.EMBEDDER_MODEL}")

        return embedder

    def _build_pipeline(self):
        # import component classes
        from backend.models.generator import get_generator
        from backend.components.content_extractor import ContentExtractor
        from backend.components.document_retriever import DocumentStoreRetriever
        from backend.models.snapshot_extractor import SnapshotExtractor
        from backend.models.profile_extractor import ProfileExtractor
        from backend.models.entity_extractor import EntityExtractor
        from backend.models.relationship_extractor import RelationshipExtractor
        from backend.models.reranker import Reranker
        from backend.models.fact_checker import FactChecker

        # create default llm generator
        llm_generator = get_generator(self.config, self.config.DEFAULT_OLLAMA_MODEL)
        self.current_generator = llm_generator
        self.current_model_id = self.config.DEFAULT_OLLAMA_MODEL

        # create document cleaner
        document_cleaner = DocumentCleaner(
            remove_empty_lines=True,
            remove_extra_whitespaces=True,
            remove_repeated_substrings=False,
        )
        print("[PIPELINE] DocumentCleaner: Haystack built-in")

        # create document splitter
        document_splitter = DocumentSplitter(
            split_by="sentence",
            split_length=self.config.DOCUMENT_SPLIT_LENGTH,
            split_overlap=self.config.DOCUMENT_SPLIT_OVERLAP,
        )
        print(
            "[PIPELINE] DocumentSplitter: Haystack built-in "
            f"(length: {self.config.DOCUMENT_SPLIT_LENGTH})"
        )

        # build fact checker component
        if self.config.ENABLE_FACT_CHECKING:
            fact_checker = FactChecker(config=self.config)
        else:
            fact_checker = None

        # build entity extractor component
        if self.config.ENABLE_ENTITY_EXTRACTION:
            entity_extractor = EntityExtractor(config=self.config)
        else:
            entity_extractor = None

        # build relationship extractor component
        if self.config.ENABLE_RELATIONSHIPS:
            relationship_extractor = RelationshipExtractor(config=self.config)
        else:
            relationship_extractor = None

        # build reranker component
        if self.config.PIPELINE_ENABLE_RERANKING:
            reranker = Reranker(config=self.config)
        else:
            reranker = None

        # store component refs
        self.components = {
            "content_extractor": ContentExtractor(config=self.config),
            "document_cleaner": document_cleaner,
            "document_splitter": document_splitter,
            "llm": llm_generator,
            "snapshot_extractor": SnapshotExtractor(config=self.config),
            "profile_extractor": ProfileExtractor(config=self.config),
            "fact_checker": fact_checker,
            "entity_extractor": entity_extractor,
            "relationship_extractor": relationship_extractor,
            "reranker": reranker,
            "db_retriever": DocumentStoreRetriever(
                config=self.config,
                document_store=self.document_store,
                embedder=self.embedder,
            ),
        }

        # set active retrievers
        self.retriever_names = []

    def _warm_up_components(self):
        # warm up component registry
        print("[PIPELINE] Warming up components...")

        for name, component in self.components.items():
            # skip empty component
            comp = component
            if not comp:
                continue

            # warm up supported components
            if hasattr(comp, "warm_up"):
                print(f"[PIPELINE] warming up {name}...")
                comp.warm_up()
                print(f"[PIPELINE] {name} warmed up")

    def _get_generator(self, model_id: str = None):
        # get generator for model id
        from backend.models.generator import get_generator

        # set default model id
        if not model_id:
            model_id = self.config.DEFAULT_OLLAMA_MODEL

        # reuse cached generator
        if model_id == self.current_model_id and self.current_generator:
            return self.current_generator

        # create new generator
        generator = get_generator(self.config, model_id)
        self.current_generator = generator
        self.current_model_id = model_id

        # warm up generator
        if hasattr(generator, "warm_up"):
            generator.warm_up()

        # store generator in registry
        self.components["llm"] = generator

        return generator

    def run(self, query: str, model_id: str = None):
        # run pipeline for query
        start_time = time.time()
        timings = {}

        # load generator for model
        llm = self._get_generator(model_id)

        # import query builder
        from backend.helpers.fetch.query_helpers import build_expanded_queries
        from backend.configuration.profile import PROFILE_QUERY_SUFFIXES
        from backend.configuration.case import CASE_QUERY_SUFFIXES

        # merge suffix list
        suffixes = list(PROFILE_QUERY_SUFFIXES or []) + list(CASE_QUERY_SUFFIXES or [])

        # build query list
        all_queries = build_expanded_queries(
            config=self.config,
            query=query,
            suffixes=suffixes,
        )

        # print query stats
        if len(all_queries) > 1:
            print(f"[PIPELINE] query expansion: {len(all_queries)} variants")
        else:
            print("[PIPELINE] query expansion: single query")

        # run retrievers
        print("\n[PIPELINE] Running retrievers...")
        t_ret = time.time()
        retriever_results = self._run_retrievers(all_queries)
        timings["retrievers"] = time.time() - t_ret

        # compute total docs
        total_docs = sum(len(docs) for docs in retriever_results.values())
        if total_docs == 0:
            # build empty response
            print("\n[PIPELINE] No documents found - returning empty result")
            timings["total_time"] = time.time() - start_time
            empty = self._empty_result()
            empty["timings"] = timings
            self._log_timings(timings)
            return empty

        print(f"\n[PIPELINE] Total documents: {total_docs}")

        # flatten and dedupe docs
        t_flat = time.time()
        all_documents = self._flatten_and_dedupe_documents(retriever_results)
        timings["flatten_dedupe"] = time.time() - t_flat

        print(f"[PIPELINE] After deduplication: {len(all_documents)} unique documents")

        # run summarization
        first_pass = self._summarize_from_documents(
            query=query,
            llm=llm,
            all_documents=all_documents,
        )

        if not first_pass:
            # build empty response
            print("[PIPELINE] summarization produced no output - returning empty")
            timings["total_time"] = time.time() - start_time
            empty = self._empty_result()
            empty["timings"] = timings
            self._log_timings(timings)
            return empty

        # read output payload
        output = first_pass["output"]

        # merge timing map
        first_timings = first_pass.get("timings", {})
        for key, value in first_timings.items():
            timings[f"first_{key}"] = value

        # attach model id
        output["model_id"] = self.current_model_id

        # store total time
        total_time = time.time() - start_time
        print(f"\n[PIPELINE] Completed in {total_time:.1f}s")

        timings["total_time"] = total_time
        output["timings"] = timings

        # print timing table
        self._log_timings(timings)

        return output