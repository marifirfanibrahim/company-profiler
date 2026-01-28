"""
retrieval helpers
run source retrievers
"""

import time
import concurrent.futures


# ==================== RETRIEVAL MIXIN ====================

class RetrievalMixin:

    def _run_retrievers(self, queries: list) -> dict:
        # run retrievers in parallel using thread pool
        results = {name: [] for name in self.retriever_names}
        results["db_retriever"] = []

        # build task list
        tasks = []
        for query in queries:
            # queue source tasks
            for name in self.retriever_names:
                tasks.append((name, query))

            # queue db task
            tasks.append(("db_retriever", query))

        # compute task count
        total_tasks = len(tasks)
        print(f"[PIPELINE] Running {total_tasks} retriever tasks...")

        # read pool settings
        max_workers = self.config.RETRIEVER_MAX_WORKERS
        task_timeout = self.config.RETRIEVER_TASK_TIMEOUT
        global_timeout = self.config.RETRIEVER_GLOBAL_TIMEOUT

        # init counters
        start_time = time.time()
        completed = 0
        failed = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # map futures to task tuple
            future_to_task = {}

            for name, query in tasks:
                # load component
                component = self.components.get(name)

                # submit task
                future = executor.submit(component.run, query=query)
                future_to_task[future] = (name, query)

            try:
                # iterate futures with global timeout
                for future in concurrent.futures.as_completed(
                    future_to_task, timeout=global_timeout
                ):
                    name, query = future_to_task[future]
                    try:
                        # compute remaining time
                        elapsed = time.time() - start_time
                        remaining_global = max(0.1, global_timeout - elapsed)

                        # compute per task timeout
                        single_timeout = min(task_timeout, remaining_global)

                        # read task result
                        result = future.result(timeout=single_timeout)

                        # read doc list
                        docs = result.get("documents", []) if isinstance(result, dict) else []

                        # store results
                        results[name].extend(docs)
                        completed += 1
                    except concurrent.futures.TimeoutError:
                        # count timeout
                        failed += 1
                        print(f"[PIPELINE] {name} timeout")
                        future.cancel()
                    except Exception as e:
                        # count task error
                        failed += 1
                        print(f"[PIPELINE] {name} error: {e}")
            except concurrent.futures.TimeoutError:
                # handle global timeout
                print(f"[PIPELINE] global retriever timeout after {global_timeout}s")
                for future in future_to_task:
                    if not future.done():
                        future.cancel()

        # print pool stats
        print(f"[PIPELINE] Completed {completed}/{total_tasks} tasks ({failed} failed)")

        return results

    def _doc_rank(self, doc) -> float:
        # compute doc rank score
        meta = doc.meta or {}

        # read relevance score
        rel = meta.get("relevance_score")
        if rel is not None:
            return float(rel)

        # read doc score
        score = getattr(doc, "score", None)
        if score is not None:
            return float(score)

        return 0.0

    def _flatten_and_dedupe_documents(self, retriever_results: dict) -> list:
        # flatten documents and dedupe by url then content overlap
        by_url = {}
        no_url = []

        for docs in retriever_results.values():
            for doc in docs:
                # read url meta
                meta = doc.meta or {}
                url = str(meta.get("url", "") or "").strip()

                if url:
                    # select best doc per url
                    existing = by_url.get(url)
                    if existing is None:
                        by_url[url] = doc
                    else:
                        new_rank = self._doc_rank(doc)
                        old_rank = self._doc_rank(existing)
                        if new_rank > old_rank:
                            by_url[url] = doc
                else:
                    # store no url docs
                    no_url.append(doc)

        # merge docs
        all_docs = list(by_url.values()) + list(no_url)

        # sort by rank
        all_docs = sorted(all_docs, key=self._doc_rank, reverse=True)

        kept = []
        threshold = self.config.DEDUPE_CONTENT_JACCARD

        def _word_set(text: str):
            # build token set
            if not text:
                return set()

            # normalize text
            s = str(text).lower()

            # import re local
            import re

            # read min word len
            min_word = self.config.DEDUPE_MIN_WORD_LENGTH

            # extract words
            words = re.findall(rf"\b[a-z0-9]{{{min_word},}}\b", s)
            return set(words)

        # clamp content size
        max_chars = self.config.DEDUPE_MAX_CHARS

        for doc in all_docs:
            # clamp doc content
            content = (doc.content or "")[:max_chars]

            # build doc token set
            ws = _word_set(content)

            is_dup = False
            for existing in kept:
                # build existing token set
                existing_ws = _word_set((existing.content or "")[:max_chars])
                if not ws or not existing_ws:
                    continue

                # compute jaccard
                inter = len(ws & existing_ws)
                uni = len(ws | existing_ws)
                j = (inter / uni) if uni > 0 else 0.0

                # mark duplicate
                if j >= threshold:
                    is_dup = True
                    break

            # keep non duplicate
            if not is_dup:
                kept.append(doc)

        return kept