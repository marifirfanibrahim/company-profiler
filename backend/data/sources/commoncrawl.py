"""
common crawl retriever
fetch archived web pages
search multiple crawl indices
maximize data volume for filtering
parallel content fetching
"""

import re
import gzip
import json
import concurrent.futures
from typing import List, Dict, Any, Set

from haystack.core.component import component
from haystack.dataclasses import Document

import trafilatura

from backend.configuration.sources import (
    COMMONCRAWL_INDICES,
    COMMONCRAWL_INDEX_URL,
    COMMONCRAWL_S3_BASE,
    COMMONCRAWL_TARGET_DOMAINS,
    USER_AGENT_BOT,
)
from backend.helpers.fetch.source_helpers import create_document, log_results
from backend.helpers.fetch.httpx_helpers import build_httpx_client, resolve_tls_verify


# ==================== COMMON CRAWL RETRIEVER ====================

@component
class CommonCrawlRetriever:

    def __init__(self, config):
        # store config and settings
        self.config = config
        self.source_id = "commoncrawl"
        self.name = "Common Crawl"

        # read config values
        self.timeout = int(config.COMMONCRAWL_TIMEOUT)
        self.max_results = int(config.COMMONCRAWL_MAX_RESULTS)
        self.max_index_hits = int(config.COMMONCRAWL_MAX_INDEX_HITS)
        self.fetch_workers = int(config.COMMONCRAWL_FETCH_WORKERS)
        self.max_indices = int(config.COMMONCRAWL_MAX_INDICES)
        self.hits_per_index = int(config.COMMONCRAWL_HITS_PER_INDEX)

        # store static config
        self.crawl_indices = COMMONCRAWL_INDICES
        self.index_url_template = COMMONCRAWL_INDEX_URL
        self.s3_base = COMMONCRAWL_S3_BASE
        self.target_domains = COMMONCRAWL_TARGET_DOMAINS
        self.user_agent = USER_AGENT_BOT

        # log active indices
        indices_str = ", ".join(self.crawl_indices[: self.max_indices])
        print(f"[SOURCE] {self.source_id} ({self.name}) initialized | indices: {indices_str}")

    def _get_headers(self) -> Dict[str, str]:
        # build request headers
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
        }

        # force connection close
        if bool(self.config.COMMONCRAWL_FORCE_CONNECTION_CLOSE):
            headers["Connection"] = "close"

        return headers

    def _build_index_client(self):
        # build index client
        return build_httpx_client(
            config=self.config,
            timeout=self.timeout,
            headers=self._get_headers(),
            follow_redirects=bool(self.config.HTTP_FOLLOW_REDIRECTS),
            verify=resolve_tls_verify(self.config, source_id=self.source_id),
            force_connection_close=bool(self.config.COMMONCRAWL_FORCE_CONNECTION_CLOSE),
        )

    @component.output_types(documents=List[Document])
    def run(self, query: str) -> Dict[str, Any]:
        # run main retrieval
        documents: List[Document] = []

        # normalize query
        full_query = str(query or "").strip()
        if not full_query:
            log_results(self.source_id, documents, "no query")
            return {"documents": []}

        # build patterns
        patterns = self._build_query_patterns(full_query)
        if not patterns:
            log_results(self.source_id, documents, "no patterns")
            return {"documents": []}

        # print pattern list
        print(f"[COMMONCRAWL] patterns: {patterns}")

        # search indices
        index_results = self._search_multiple_indices(patterns)
        if not index_results:
            log_results(self.source_id, documents, "no index matches")
            return {"documents": []}

        # print index hit count
        print(f"[COMMONCRAWL] Found {len(index_results)} index hits, fetching content...")

        # fetch html records
        documents = self._fetch_all_content(index_results)

        # log final stats
        log_results(self.source_id, documents, f"index: {len(index_results)}")

        return {"documents": documents}

    def _build_query_patterns(self, query: str) -> List[str]:
        # build url patterns from query tokens
        q = str(query or "").strip().lower()
        if not q:
            return []

        # normalize whitespace
        q = re.sub(r"\s+", " ", q).strip()
        if not q:
            return []

        # build variants
        hyphen = re.sub(r"\s+", "-", q).strip("-")
        concat = re.sub(r"\s+", "", q)

        patterns: List[str] = []
        if hyphen:
            patterns.append(hyphen)
        if concat and concat != hyphen:
            patterns.append(concat)

        # read limit from config
        limit = int(self.config.COMMONCRAWL_PATTERN_LIMIT)

        out: List[str] = []
        seen = set()
        for p in patterns:
            # dedupe patterns
            key = p.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(p)

        return out[:limit]

    def _search_multiple_indices(self, patterns: List[str]) -> List[Dict]:
        # search many indices
        all_results: List[Dict] = []
        seen_urls: Set[str] = set()

        # clamp indices list
        indices_to_search = self.crawl_indices[: self.max_indices]

        # read domain limit
        domain_limit = int(self.config.COMMONCRAWL_DOMAIN_SCAN_LIMIT)

        with self._build_index_client() as client:
            for crawl_id in indices_to_search:
                # stop on cap
                if len(all_results) >= self.max_index_hits:
                    break

                # build index url
                index_url = self.index_url_template.format(crawl_id=crawl_id)
                print(f"[COMMONCRAWL] Searching index: {crawl_id}")

                # search one index
                hits = self._search_single_index(
                    client=client,
                    index_url=index_url,
                    patterns=patterns,
                    seen_urls=seen_urls,
                    domain_limit=domain_limit,
                )

                # append hits with crawl id
                for hit in hits:
                    # attach crawl id
                    hit["crawl_id"] = crawl_id
                    all_results.append(hit)

                    # enforce global cap
                    if len(all_results) >= self.max_index_hits:
                        break

                # print per index status
                print(f"[COMMONCRAWL] {crawl_id}: {len(hits)} hits")

        return all_results[: self.max_index_hits]

    def _search_single_index(
        self,
        client,
        index_url: str,
        patterns: List[str],
        seen_urls: Set[str],
        domain_limit: int,
    ) -> List[Dict]:
        # search one index
        results: List[Dict] = []

        # scan target domains first
        for domain in self.target_domains[:domain_limit]:
            # stop on cap
            if len(results) >= self.hits_per_index:
                break

            for pat in patterns:
                # stop on cap
                if len(results) >= self.hits_per_index:
                    break

                # build domain scoped pattern
                url_pattern = f"*.{domain}/*{pat}*"

                # query index
                hits = self._query_index(client, index_url, url_pattern=url_pattern)

                # append unique
                self._add_unique(hits, results, seen_urls)

        # scan global pattern
        for pat in patterns:
            # stop on cap
            if len(results) >= self.hits_per_index:
                break

            # query index
            hits = self._query_index(client, index_url, url_pattern=f"*{pat}*")

            # append unique
            self._add_unique(hits, results, seen_urls)

        return results[: self.hits_per_index]

    def _query_index(
        self,
        client,
        index_url: str,
        url_pattern: str,
    ) -> List[Dict]:
        # query index api
        results: List[Dict] = []

        # build query params
        params = {
            "url": url_pattern,
            "output": "json",
            "limit": int(self.config.COMMONCRAWL_QUERY_LIMIT),
        }

        # run request
        response = client.get(index_url, params=params)

        if response.status_code != 200:
            # print status line
            print(
                f"[COMMONCRAWL] index status {response.status_code} "
                f"for pattern {url_pattern}"
            )
            return []

        for line in response.text.strip().split("\n"):
            # skip empty line
            if not line:
                continue

            # parse record json
            record = json.loads(line)

            # accept status 200
            if record.get("status") == "200":
                results.append(record)

        return results

    def _add_unique(self, hits: List[Dict], results: List[Dict], seen: Set[str]):
        # avoid duplicate urls
        for hit in hits:
            # read url
            url = hit.get("url", "")
            if not url:
                continue

            # dedupe url
            if url in seen:
                continue

            # store url
            seen.add(url)
            results.append(hit)

    def _fetch_all_content(self, records: List[Dict]) -> List[Document]:
        # fetch content in parallel
        documents: List[Document] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.fetch_workers) as executor:
            # build future map
            future_to_record = {
                executor.submit(self._fetch_single, record): record
                for record in records
            }

            for future in concurrent.futures.as_completed(future_to_record):
                # skip failed future
                exc = future.exception()
                if exc is not None:
                    continue

                # read doc object
                doc = future.result()
                if doc:
                    documents.append(doc)

                    # stop on cap
                    if len(documents) >= self.max_results:
                        for f in future_to_record:
                            f.cancel()
                        break

        return documents

    def _fetch_single(self, record: Dict) -> Document:
        # fetch single warc record
        filename = record.get("filename", "")
        offset = int(record.get("offset", 0))
        length = int(record.get("length", 0))
        url = record.get("url", "")
        timestamp = record.get("timestamp", "")
        crawl_id = record.get("crawl_id", "")

        # validate record
        if not filename or not length:
            return None

        # build s3 url
        s3_url = f"{self.s3_base}/{filename}"

        # build range header
        headers = self._get_headers()
        headers["Range"] = f"bytes={offset}-{offset + length - 1}"

        with build_httpx_client(
            config=self.config,
            timeout=self.timeout,
            headers=headers,
            follow_redirects=bool(self.config.HTTP_FOLLOW_REDIRECTS),
            verify=resolve_tls_verify(self.config, source_id=self.source_id),
            force_connection_close=bool(self.config.COMMONCRAWL_FORCE_CONNECTION_CLOSE),
        ) as client:
            # fetch byte range
            response = client.get(s3_url)

            # validate status code
            if response.status_code not in [200, 206]:
                return None

            # decompress warc record
            decompressed = gzip.decompress(response.content)
            warc_data = decompressed.decode("utf-8", errors="ignore")

        # parse http payload section
        html = warc_data
        sep1 = html.find("\r\n\r\n")
        if sep1 != -1:
            http_block = html[sep1 + 4:]
            sep2 = http_block.find("\r\n\r\n")
            if sep2 != -1:
                html = http_block[sep2 + 4:]
            else:
                html = http_block

        # extract content with trafilatura
        content = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=True,
        )

        # validate content length
        min_len = int(self.config.COMMONCRAWL_MIN_CONTENT_LENGTH)
        if not content or len(content) < min_len:
            return None

        # build title
        title = self._extract_title(html) or url[: int(self.config.TITLE_TRUNCATE_LENGTH)]

        # parse timestamp date
        source_date = None
        if len(timestamp) >= 8:
            source_date = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"

        # read clamps
        snippet_len = int(self.config.SNIPPET_LENGTH)
        max_content_chars = int(self.config.COMMONCRAWL_MAX_CONTENT_CHARS)

        return create_document(
            source_name=f"{self.name} ({crawl_id})" if crawl_id else self.name,
            title=title,
            url=url,
            snippet=content[:snippet_len],
            content=content[:max_content_chars],
            source_date=source_date,
        )

    def _extract_title(self, html: str) -> str:
        # extract page title
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            # normalize title
            title = match.group(1).strip()
            title = re.sub(r"\s+", " ", title)
            return title[:200]
        return ""