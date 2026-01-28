"""
seed chromadb
fetch online docs
warm cache
"""

import time
import random
import json
import concurrent.futures
from datetime import datetime, timezone
from typing import List, Dict, Set, Any, Tuple


# ==================== IMPORTS ====================

from backend.configuration.config import get_config
from backend.configuration.paths import SEED_URLS_PATH, SEED_ENTITIES_PATH, SEED_ENTITY_CANDIDATES_PATH
from backend.configuration.seeding import (
    SEED_ACTIVE_RETRIEVERS,
    SEED_ROUND_DELAY,
    SEED_MAX_ROUNDS,
    SEED_CONTENT_EXTRACT_MAX_DOCS,
    SEED_RERANK_SKIP_SOURCES,
    SEED_BASE_SOURCE_CACHE_ENABLED,
    SEED_BASE_SOURCE_CACHE_TTL_SECONDS,
    SEED_BASE_SOURCE_CACHE_SOURCES,
    SEED_DYNAMIC_RELOAD_ENABLED,
    SEED_DYNAMIC_RELOAD_EVERY_ROUNDS,
    SEED_DYNAMIC_PROMOTE_EVERY_ROUNDS,
    SEED_DYNAMIC_PRIORITY_ENABLED,
    SEED_DYNAMIC_PRIORITY_MAX_ENTITIES,
    SEED_DYNAMIC_PRIORITY_MAX_QUERIES_PER_ENTITY,
    SEED_DYNAMIC_PRIORITY_PREFER_BASE_QUERY,
    SEED_CONCURRENT_ITEMS_ENABLED,
    SEED_CONCURRENT_ITEMS_PER_BATCH,
    SEED_CONCURRENT_ITEMS_WORKERS,
)
from backend.configuration.profile import PROFILE_QUERY_SUFFIXES
from backend.configuration.case import CASE_QUERY_SUFFIXES
from backend.configuration.sources import OFFICIAL_CASE_SOURCES
from backend.data.document_store import get_document_store
from backend.data.sources.factory import get_all_retrievers
from backend.components.content_extractor import ContentExtractor
from backend.models.reranker import Reranker
from backend.helpers.persist.json_utils import load_json
from backend.helpers.persist.store_helpers import sanitize_meta
from backend.helpers.logic.helper import apply_hf_hub_env
from backend.helpers.logic.seed_helpers import promote_seed_entity_candidates


# ==================== SEEN URLS ====================

def load_seen_urls() -> Set[str]:
    # load seen urls
    if not SEED_URLS_PATH.exists():
        return set()

    # load json file
    data = load_json(SEED_URLS_PATH, default=[])

    if isinstance(data, list):
        # build url set
        out = set()

        for item in data:
            # normalize url string
            s = str(item or "").strip()
            if not s:
                continue
            out.add(s)

        return out

    # return empty set
    return set()


def save_seen_urls(urls: Set[str]) -> None:
    # save seen urls
    SEED_URLS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # sort url list
    items = sorted(list(urls))

    # write json file
    with SEED_URLS_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


# ==================== MODELS ====================

def init_embedder(model_name: str):
    # init sentence embedder
    from sentence_transformers import SentenceTransformer

    # normalize model name
    m = str(model_name or "").strip()

    # build embedder instance
    embedder = SentenceTransformer(m)

    # print status
    print(f"[SEED] embedder loaded: {m}")

    return embedder


# ==================== ENTITIES ====================

def load_seed_entities() -> List[str]:
    # load seed names
    entities: List[str] = []

    if SEED_ENTITIES_PATH.exists():
        # load json file
        data = load_json(SEED_ENTITIES_PATH, default=[])

        if isinstance(data, list):
            for item in data:
                # validate item type
                if not isinstance(item, str):
                    continue

                # normalize string
                s = item.strip()
                if not s:
                    continue

                # strip quotes
                if s.startswith('"'):
                    s = s[1:].strip()
                if s.endswith('"'):
                    s = s[:-1].strip()

                # normalize final string
                s = s.strip()
                if not s:
                    continue

                entities.append(s)

    if not entities:
        # print empty status
        print("[SEED] no seed_entities.json found or list empty")
        return []

    deduped: List[str] = []
    seen = set()

    for s in entities:
        # build dedupe key
        key = s.lower()

        # skip duplicates
        if key in seen:
            continue

        # store unique item
        seen.add(key)
        deduped.append(s)

    # print load summary
    print(f"[SEED] loaded {len(deduped)} seed entities from json")

    return deduped


def build_seed_queries(entities: List[str]) -> List[Dict[str, str]]:
    # build seed queries from base and suffixes
    profile_suffixes = list(PROFILE_QUERY_SUFFIXES or [])
    case_suffixes = list(CASE_QUERY_SUFFIXES or [])

    # merge suffix lists
    suffixes = profile_suffixes + case_suffixes

    queries: List[Dict[str, str]] = []
    seen_full = set()

    for name in entities:
        # normalize base
        base = name.strip()
        if not base:
            continue

        # add base query
        full_base = base
        key_base = full_base.lower()

        if key_base not in seen_full:
            # store base query
            seen_full.add(key_base)
            queries.append({"base": base, "query": full_base})

        # add suffix queries
        for suffix in suffixes:
            # normalize suffix
            s_clean = str(suffix).strip()
            if not s_clean:
                continue

            # build full query
            full = f"{base} {s_clean}".strip()
            key = full.lower()

            # skip duplicates
            if key in seen_full:
                continue

            # store query item
            seen_full.add(key)
            queries.append({"base": base, "query": full})

    # print build summary
    print(f"[SEED] built {len(queries)} seed queries from {len(entities)} entities")

    return queries


# ==================== CACHE ====================

def _cache_is_enabled() -> bool:
    # read cache enabled flag
    return bool(SEED_BASE_SOURCE_CACHE_ENABLED)


def _cache_ttl_seconds() -> int:
    # read cache ttl
    return int(SEED_BASE_SOURCE_CACHE_TTL_SECONDS)


def _cache_get(base_source_cache: dict, key: Tuple[str, str]) -> List:
    # get cached docs if valid
    if not _cache_is_enabled():
        return []

    # read ttl value
    ttl = _cache_ttl_seconds()
    if ttl <= 0:
        return []

    # read cache entry
    entry = base_source_cache.get(key)
    if not isinstance(entry, dict):
        return []

    # read cache fields
    saved_at = float(entry.get("saved_at", 0.0) or 0.0)
    docs = entry.get("docs")

    # validate docs list
    if not isinstance(docs, list):
        return []

    # compute cache age
    age = time.time() - saved_at
    if age > float(ttl):
        return []

    # return cached docs
    return list(docs)


def _cache_set(base_source_cache: dict, key: Tuple[str, str], docs: List) -> None:
    # store docs into cache
    if not _cache_is_enabled():
        return

    # read ttl value
    ttl = _cache_ttl_seconds()
    if ttl <= 0:
        return

    # store cache row
    base_source_cache[key] = {
        "saved_at": float(time.time()),
        "docs": list(docs or []),
    }


# ==================== FETCH ====================

def fetch_documents_for_seed(
    seed_item: Dict[str, str],
    retrievers: Dict[str, object],
    config_cls,
    base_source_cache: Dict[Tuple[str, str], Dict[str, Any]],
) -> List:
    # run active retrievers and skip failures
    all_docs = []

    # read query fields
    full_query = seed_item.get("query", "").strip()
    base_query = seed_item.get("base", "").strip()

    # build base cache source set
    base_sources = set(
        str(x or "").strip()
        for x in (SEED_BASE_SOURCE_CACHE_SOURCES or [])
        if str(x or "").strip()
    )

    tasks = []
    for name, component in retrievers.items():
        # skip inactive retriever
        if name not in SEED_ACTIVE_RETRIEVERS:
            continue

        # choose query per source
        if name in base_sources:
            q = base_query
        else:
            q = full_query

        # apply cache for base sources
        if name in base_sources:
            # build cache key
            cache_key = (name, q)

            # read cached docs
            cached = _cache_get(base_source_cache, cache_key)
            if cached:
                print(f"[SEED] {name}: using cache for '{q}' ({len(cached)} docs)")
                all_docs.extend(cached)
                continue

        # queue task item
        tasks.append((name, component, q))

    # stop on empty task list
    if not tasks:
        return all_docs

    # read max workers from config
    max_workers = int(config_cls.RETRIEVER_MAX_WORKERS)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # map futures to retriever id
        future_map = {}

        for name, component, q in tasks:
            # print fetch status
            print(f"[SEED] {name}: fetching for '{q}'")

            # submit retriever job
            future = executor.submit(component.run, query=q)

            # store future key
            future_map[future] = (name, q)

        for future in concurrent.futures.as_completed(future_map):
            # read task metadata
            name, q = future_map[future]

            # skip failed retriever
            exc = future.exception()
            if exc is not None:
                err = type(exc).__name__
                print(f"[SEED] {name}: skipped ({err})")
                continue

            # collect docs
            result = future.result()
            docs = result.get("documents", []) if isinstance(result, dict) else []

            # print doc count
            if docs:
                print(f"[SEED] {name}: {len(docs)} docs")

            # store base cache
            if name in base_sources and q:
                _cache_set(base_source_cache, (name, q), list(docs))

            # append docs
            all_docs.extend(docs)

    return all_docs


def fetch_and_extract_for_seed(
    seed_item: Dict[str, str],
    retrievers: Dict[str, object],
    config_cls,
    base_source_cache: Dict[Tuple[str, str], Dict[str, Any]],
    content_extractor: ContentExtractor,
) -> Dict[str, Any]:
    # fetch and extract docs for seed item
    raw_docs = fetch_documents_for_seed(
        seed_item=seed_item,
        retrievers=retrievers,
        config_cls=config_cls,
        base_source_cache=base_source_cache,
    )

    # stop on empty fetch
    if not raw_docs:
        return {
            "seed_item": seed_item,
            "documents": [],
        }

    # run extraction
    extracted = content_extractor.run(
        documents=list(raw_docs),
        max_docs=int(SEED_CONTENT_EXTRACT_MAX_DOCS),
    )

    # read extracted docs
    docs_with_content = extracted.get("documents", []) if isinstance(extracted, dict) else []

    return {
        "seed_item": seed_item,
        "documents": docs_with_content,
    }


# ==================== INDEX ====================

def index_documents_into_chroma(
    docs: List,
    doc_store,
    embedder,
    config,
    reranker: Reranker,
    seed_query: str,
    company_name: str,
    seen_urls: Set[str]
) -> int:
    # filter and index docs
    if not docs or not doc_store or not embedder:
        return 0

    # print rerank status
    print(f"[SEED] reranking {len(docs)} docs for '{seed_query}'")

    # normalize company name
    company_name = (company_name or "").strip()

    # read config values
    min_len = int(config.DATABASE_MIN_CONTENT_LENGTH)
    max_docs = int(config.DATABASE_MAX_INDEX_DOCS)
    truncate_len = int(config.DATABASE_INDEX_TRUNCATE_LENGTH)

    # build skip source set
    skip_sources = set(
        str(s or "").strip()
        for s in (SEED_RERANK_SKIP_SOURCES or [])
        if str(s or "").strip()
    )

    official_docs = []
    skip_rerank_docs = []
    other_docs = []

    for doc in docs:
        # read meta
        meta = doc.meta or {}

        # read source name
        source_name = str(meta.get("source") or "").strip()

        # split by source rule
        if source_name in OFFICIAL_CASE_SOURCES:
            official_docs.append(doc)
        elif source_name in skip_sources:
            skip_rerank_docs.append(doc)
        else:
            other_docs.append(doc)

    filtered_docs: List = []

    # apply reranker only to remaining docs
    if other_docs:
        # rerank on seed query
        if seed_query and seed_query.strip():
            rr = reranker.run(query=seed_query, documents=other_docs)
            rr_docs = rr.get("documents", []) if isinstance(rr, dict) else []

            # merge rerank output
            if rr_docs:
                filtered_docs.extend(rr_docs)
            else:
                filtered_docs.extend(other_docs)
        else:
            # pass through docs
            filtered_docs.extend(other_docs)

    # merge doc lists
    combined_docs: List = list(official_docs) + list(skip_rerank_docs) + list(filtered_docs)
    if not combined_docs:
        print("[SEED] index skip: no combined docs")
        return 0

    texts: List[str] = []
    metas: List[Dict[str, Any]] = []
    new_urls: Set[str] = set()

    dropped_min_len = 0
    dropped_seen = 0

    by_source_pass: Dict[str, int] = {}

    # build indexed stamp
    date_fmt = str(config.DATE_STAMP_FORMAT)
    indexed_at = datetime.now(timezone.utc).strftime(date_fmt)

    for doc in combined_docs:
        # read fields
        content = (doc.content or "").strip()
        meta_in = doc.meta or {}

        # skip short content
        if not content or len(content) < min_len:
            dropped_min_len += 1
            continue

        # skip seen urls
        url = str(meta_in.get("url", "") or "").strip()
        if url and url in seen_urls:
            dropped_seen += 1
            continue

        # apply truncate
        if truncate_len > 0:
            content = content[:truncate_len]

        # sanitize meta
        meta_clean = sanitize_meta(meta_in)

        # set seed flags
        meta_clean["is_seeded"] = True
        meta_clean["seed_query"] = seed_query
        meta_clean["seed_company"] = company_name
        meta_clean["embedder_model"] = config.EMBEDDER_MODEL
        meta_clean["reranker_model"] = config.RERANKER_MODEL
        meta_clean["indexed_at"] = indexed_at

        # store text and meta
        texts.append(content)
        metas.append(meta_clean)

        # count sources
        src = str(meta_clean.get("source") or "").strip() or "unknown"
        by_source_pass[src] = int(by_source_pass.get(src, 0)) + 1

        # track new urls
        if url:
            new_urls.add(url)

        # enforce cap
        if len(texts) >= max_docs:
            break

    if not texts:
        print(
            "[SEED] index skip: no texts "
            f"(min_len={dropped_min_len}, seen={dropped_seen})"
        )
        return 0

    # print source breakdown
    src_items = ", ".join(
        [f"{k}={v}" for k, v in sorted(by_source_pass.items(), key=lambda x: x[0].lower())]
    )
    print(f"[SEED] index pass: {len(texts)} docs (min_len={dropped_min_len}, seen={dropped_seen})")
    print(f"[SEED] index sources: {src_items}")

    # encode embeddings
    print(f"[SEED] encoding {len(texts)} docs for chroma")
    embeddings = embedder.encode(texts)
    if hasattr(embeddings, "tolist"):
        embeddings = embeddings.tolist()

    payload = []
    for i, text in enumerate(texts):
        # append payload item
        payload.append(
            {
                "content": text,
                "meta": metas[i],
                "embedding": embeddings[i],
            }
        )

    # write docs to store
    doc_store.add_documents(payload)

    if new_urls:
        # update seen urls
        seen_urls.update(new_urls)

        # persist seen urls
        save_seen_urls(seen_urls)

    # return indexed count
    return len(payload)


# ==================== PRIORITY ====================

def load_promoted_priority_entities(max_entities: int, already_seen: Set[str]) -> List[str]:
    # load promoted names from candidates file
    cap = int(max_entities)

    # normalize seen set
    seen = set(
        str(x or "").lower().strip()
        for x in (already_seen or set())
        if str(x or "").strip()
    )

    # load json file
    data = load_json(SEED_ENTITY_CANDIDATES_PATH, default=[])
    if not isinstance(data, list):
        return []

    items = []
    for row in data:
        # validate row type
        if not isinstance(row, dict):
            continue

        # require promoted stamp
        promoted_at = row.get("promoted_at")
        if not promoted_at:
            continue

        # read name field
        name = str(row.get("name") or "").strip()
        if not name:
            continue

        # dedupe by seen set
        key = name.lower()
        if key in seen:
            continue

        # store sortable row
        items.append((str(promoted_at), name))

    # newest promotion first
    items.sort(key=lambda x: x[0], reverse=True)

    out: List[str] = []
    for _, name in items:
        # dedupe name
        key = name.lower()
        if key in seen:
            continue

        # store queued name
        seen.add(key)
        out.append(name)

        # enforce cap
        if cap > 0 and len(out) >= cap:
            break

    return out


# ==================== MAIN ====================

def run_seed_rounds(env: str = None, rounds: int = None):
    # run seed rounds
    from backend.configuration.seeding import SEED_ENV

    # normalize env value
    if env is None:
        env = SEED_ENV

    # load config class
    config_cls = get_config(env)

    # build config instance
    config = config_cls()

    # apply hf hub env
    apply_hf_hub_env(config)

    # seed expansion promotion pass
    promo = promote_seed_entity_candidates()
    if int(promo.get("promoted", 0)) > 0:
        print(
            "[SEED_EXPANSION] "
            f"promoted={promo.get('promoted', 0)}, "
            f"candidates_total={promo.get('candidates_total', 0)}, "
            f"seed_total={promo.get('seed_total', 0)}"
        )

    # track run start
    start_time = time.time()

    # init stores and models
    doc_store = get_document_store(config_cls)
    embedder = init_embedder(config_cls.EMBEDDER_MODEL)
    content_extractor = ContentExtractor(config=config_cls)
    reranker = Reranker(config=config_cls)

    # print seeding mode
    print("[SEED] seeding using json entity list")

    # stop on missing dependencies
    if not doc_store or not embedder:
        print("[SEED] document store or embedder not available")
        return

    # init retrievers
    retrievers = get_all_retrievers(config_cls)

    # compute active retrievers
    active = sorted(set(SEED_ACTIVE_RETRIEVERS) & set(retrievers.keys()))
    print(f"[SEED] active retrievers: {', '.join(active)}")

    # load seed plan
    entities = load_seed_entities()
    if not entities:
        print("[SEED] no seed queries available")
        return

    # build seed items
    seed_items = build_seed_queries(entities)
    if not seed_items:
        print("[SEED] no seed queries built")
        return

    # load seen urls
    seen_urls = load_seen_urls()
    if seen_urls:
        print(f"[SEED] loaded {len(seen_urls)} seen urls")

    # init cache map
    base_source_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}

    # read dynamic settings
    dynamic_reload = bool(SEED_DYNAMIC_RELOAD_ENABLED)
    reload_every = int(SEED_DYNAMIC_RELOAD_EVERY_ROUNDS)
    promote_every = int(SEED_DYNAMIC_PROMOTE_EVERY_ROUNDS)

    # read priority settings
    priority_enabled = bool(SEED_DYNAMIC_PRIORITY_ENABLED)
    priority_max_entities = int(SEED_DYNAMIC_PRIORITY_MAX_ENTITIES)
    priority_max_queries = int(SEED_DYNAMIC_PRIORITY_MAX_QUERIES_PER_ENTITY)
    priority_prefer_base = bool(SEED_DYNAMIC_PRIORITY_PREFER_BASE_QUERY)

    # build priority queue
    priority_entities: List[str] = []
    priority_seen: Set[str] = set()
    priority_plans: Dict[str, Dict[str, Any]] = {}

    if priority_enabled:
        # load already promoted entities into queue
        boot = load_promoted_priority_entities(priority_max_entities, priority_seen)

        if boot:
            for name in boot:
                # append priority name
                priority_entities.append(name)

                # track seen key
                priority_seen.add(name.lower())

            print(f"[SEED] priority queue loaded: {len(priority_entities)} entities")

    # read rounds and delay
    total_rounds = int(rounds) if rounds is not None else int(SEED_MAX_ROUNDS)
    round_delay = int(SEED_ROUND_DELAY)

    # read batch settings
    batch_enabled = bool(SEED_CONCURRENT_ITEMS_ENABLED)
    batch_size = int(SEED_CONCURRENT_ITEMS_PER_BATCH)
    batch_workers = int(SEED_CONCURRENT_ITEMS_WORKERS)

    # clamp batch settings
    if batch_size <= 0:
        batch_size = 1
    if batch_workers <= 0:
        batch_workers = 1

    # track loop cursor
    round_idx = 1

    while round_idx <= total_rounds:
        # promote candidates during run
        force_reload = False

        if promote_every > 0 and (round_idx % promote_every) == 0:
            # promote candidates
            promo2 = promote_seed_entity_candidates()

            # handle promotion output
            if int(promo2.get("promoted", 0)) > 0:
                print(
                    "[SEED_EXPANSION] "
                    f"promoted={promo2.get('promoted', 0)}, "
                    f"candidates_total={promo2.get('candidates_total', 0)}, "
                    f"seed_total={promo2.get('seed_total', 0)}"
                )
                force_reload = True

            if priority_enabled:
                # load newly promoted names into queue
                more = load_promoted_priority_entities(priority_max_entities, priority_seen)

                if more:
                    for name in more:
                        # enforce queue cap
                        if priority_max_entities > 0 and len(priority_entities) >= priority_max_entities:
                            break

                        # build dedupe key
                        key = name.lower()

                        # skip duplicates
                        if key in priority_seen:
                            continue

                        # append queue item
                        priority_entities.append(name)
                        priority_seen.add(key)

                    if more:
                        print(f"[SEED] priority queue updated: {len(priority_entities)} entities")

        # reload seed plan during run
        if dynamic_reload and reload_every > 0 and (force_reload or (round_idx % reload_every) == 0):
            print(f"[SEED] reloading seed plan at round {round_idx}/{total_rounds}")

            # reload entity list
            entities2 = load_seed_entities()

            if entities2:
                # rebuild seed items
                seed_items2 = build_seed_queries(entities2)

                if seed_items2:
                    # apply updated plan
                    entities = entities2
                    seed_items = seed_items2
                    print(f"[SEED] seed plan updated: entities={len(entities)}, queries={len(seed_items)}")
                else:
                    print("[SEED] seed plan reload: no queries built")
            else:
                print("[SEED] seed plan reload: no entities loaded")

        # stop if empty
        if not seed_items and not priority_entities:
            print("[SEED] no seed items available, stopping")
            break

        # compute batch count
        if batch_enabled:
            batch_count = min(batch_size, (total_rounds - round_idx + 1))
        else:
            batch_count = 1

        # build batch list
        batch_items: List[Dict[str, str]] = []
        batch_priority_flags: List[bool] = []

        for _ in range(batch_count):
            # select seed item
            seed_item = None
            is_priority = False

            if priority_enabled and priority_entities:
                # choose next priority entity
                p_name = str(priority_entities[0] or "").strip()
                if p_name:
                    # read plan state
                    plan = priority_plans.get(p_name)

                    if not isinstance(plan, dict):
                        # build priority query list
                        items = build_seed_queries([p_name])

                        if priority_prefer_base:
                            # move base query first
                            base_only = []
                            for it in items:
                                if str(it.get("query") or "").strip().lower() == str(p_name).strip().lower():
                                    base_only.append(it)
                            if base_only:
                                items = base_only + [x for x in items if x not in base_only]

                        # enforce per entity cap
                        if priority_max_queries > 0 and len(items) > priority_max_queries:
                            items = items[:priority_max_queries]

                        # store plan state
                        plan = {
                            "items": items,
                            "index": 0,
                        }
                        priority_plans[p_name] = plan

                    # read plan lists
                    items = plan.get("items") if isinstance(plan.get("items"), list) else []
                    idx = int(plan.get("index", 0) or 0)

                    if items and idx < len(items):
                        # select next priority item
                        seed_item = items[idx]
                        is_priority = True

                        # advance plan index
                        plan["index"] = idx + 1
                        priority_plans[p_name] = plan
                    else:
                        # pop entity after exhausting queries
                        priority_entities.pop(0)

                        # drop plan state
                        if p_name in priority_plans:
                            del priority_plans[p_name]

            if seed_item is None:
                # fallback random selection
                if seed_items:
                    seed_item = random.choice(seed_items)

            if not isinstance(seed_item, dict):
                # stop batch build
                break

            # append batch row
            batch_items.append(seed_item)
            batch_priority_flags.append(bool(is_priority))

        # stop on empty batch
        if not batch_items:
            print("[SEED] no seed item selected, stopping")
            break

        # print batch header
        if len(batch_items) == 1:
            # print single item header
            seed_query_str = str(batch_items[0].get("query", "") or "").strip()
            flag = " | priority" if batch_priority_flags[0] else ""
            print(f"\n[SEED] round {round_idx}/{total_rounds} | query: {seed_query_str}{flag}")
        else:
            # print batch header
            end_idx = round_idx + len(batch_items) - 1
            print(f"\n[SEED] rounds {round_idx}-{end_idx}/{total_rounds} | batch={len(batch_items)}")

        # run concurrent fetch and extract
        results: List[Dict[str, Any]] = []

        # compute worker count
        pool_workers = min(int(batch_workers), len(batch_items))
        if pool_workers <= 0:
            pool_workers = 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=pool_workers) as executor:
            # submit tasks
            future_map = {}

            for i, item in enumerate(batch_items):
                # read query label
                seed_query_str = str(item.get("query", "") or "").strip()
                flag = " | priority" if batch_priority_flags[i] else ""
                print(f"[SEED] queued: {seed_query_str}{flag}")

                # submit fetch and extract job
                future = executor.submit(
                    fetch_and_extract_for_seed,
                    seed_item=item,
                    retrievers=retrievers,
                    config_cls=config_cls,
                    base_source_cache=base_source_cache,
                    content_extractor=content_extractor,
                )
                future_map[future] = item

            for future in concurrent.futures.as_completed(future_map):
                # skip failed job
                exc = future.exception()
                if exc is not None:
                    item = future_map[future]
                    q = str(item.get("query", "") or "").strip()
                    err = type(exc).__name__
                    print(f"[SEED] fetch/extract skipped: {q} ({err})")
                    continue

                # collect result
                res = future.result()
                if isinstance(res, dict):
                    results.append(res)

        # index results sequentially
        for res in results:
            # read seed item
            seed_item = res.get("seed_item") if isinstance(res, dict) else None
            if not isinstance(seed_item, dict):
                continue

            # read fields
            seed_query_str = str(seed_item.get("query", "") or "").strip()
            base_company = str(seed_item.get("base", "") or "").strip()

            # read docs
            docs_with_content = res.get("documents", []) if isinstance(res, dict) else []
            if not docs_with_content:
                print(f"[SEED] no documents after extraction for '{seed_query_str}'")
                continue

            # index docs
            indexed = index_documents_into_chroma(
                docs=list(docs_with_content),
                doc_store=doc_store,
                embedder=embedder,
                config=config,
                reranker=reranker,
                seed_query=seed_query_str,
                company_name=base_company,
                seen_urls=seen_urls,
            )
            print(f"[SEED] indexed {indexed} documents into chromadb")

        # wait next batch
        if round_delay > 0:
            time.sleep(round_delay)

        # advance loop cursor
        round_idx += len(batch_items)

    # compute run time
    total = time.time() - start_time
    hrs, rem = divmod(int(total), 3600)
    mins, secs = divmod(rem, 60)

    # print completion status
    print(f"\n[SEED] Completed run_seed_rounds in {hrs}h{mins}m{secs}s ({total:.1f}s)")


if __name__ == "__main__":
    # run seed command
    run_seed_rounds(env=None, rounds=None)