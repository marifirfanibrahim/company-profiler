"""
official sources retriever
scrape regulator sites
collect case articles
"""

import re
from typing import List, Dict, Any
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from haystack.core.component import component
from haystack.dataclasses import Document

from backend.configuration.sources import USER_AGENT
from backend.configuration.case import SC_ENFORCEMENT_URL_KEYWORDS
from backend.helpers.fetch.source_helpers import create_document, log_source_status
from backend.helpers.fetch.httpx_helpers import build_httpx_client, resolve_tls_verify


# ==================== OFFICIAL SOURCES RETRIEVER ====================

@component
class OfficialCasesRetriever:

    def __init__(self, config):
        # store config and ids
        self.config = config
        self.source_id = "official_sources"
        self.name = "Official Sources"

        # read timeouts and limits
        self.timeout = int(config.SOURCE_DEFAULT_TIMEOUT)
        self.max_results = int(config.SOURCE_DEFAULT_MAX_RESULTS)

        # define official sites with search paths
        self.sites = [
            {
                "id": "bnm",
                "name": "Bank Negara Malaysia",
                "base_url": "https://www.bnm.gov.my",
                "search_path": "/search?q={query}"
            },
            {
                "id": "sc",
                "name": "Securities Commission Malaysia",
                "base_url": "https://www.sc.com.my",
                "search_path": "/search?q={query}"
            },
            {
                "id": "sprm",
                "name": "Malaysian Anti Corruption Commission",
                "base_url": "https://www.sprm.gov.my",
                "search_path": "/index.php?id=21&page_id=84&keyword={query}"
            },
            {
                "id": "pdrm",
                "name": "Royal Malaysia Police",
                "base_url": "https://www.rmp.gov.my",
                "search_path": "/search?q={query}"
            },
            {
                "id": "agc",
                "name": "Attorney General Chambers",
                "base_url": "https://www.agc.gov.my",
                "search_path": "/search?q={query}"
            },
            {
                "id": "lom",
                "name": "Laws of Malaysia (AGC LOM)",
                "base_url": "https://lom.agc.gov.my",
                "search_path": "/search.php?search={query}&type=all&sorting=newest&lookup=all"
            },
            {
                "id": "judiciary",
                "name": "Malaysian Judiciary",
                "base_url": "https://www.kehakiman.gov.my",
                "search_path": "/ms/search/node?keys={query}"
            }
        ]

        # print site id list
        site_names = ", ".join(s["id"] for s in self.sites)
        print(f"[SOURCE] {self.source_id} ({self.name}) initialized | sites: {site_names}")

    def _get_headers(self) -> Dict[str, str]:
        # build basic headers
        return {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def _normalize_url(self, base_url: str, href: str) -> str:
        # convert relative url to absolute
        if not href:
            return "#"
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("/"):
            return base_url.rstrip("/") + href
        return base_url.rstrip("/") + "/" + href

    def _extract_generic_items(
        self,
        html: str,
        base_url: str,
        site_name: str,
        query: str
    ) -> List[Dict[str, Any]]:
        # generic extraction focused on query tokens
        soup = BeautifulSoup(html, "html.parser")

        # normalize query
        query_lower = (query or "").lower().strip()
        query_tokens = [w for w in re.findall(r"\w+", query_lower) if len(w) >= 3]

        items: List[Dict[str, Any]] = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            # read title text
            title = link.get_text(strip=True)
            if not title:
                continue

            # enforce title length
            if len(title) < 8:
                continue

            # build matching strings
            title_lower = title.lower()

            # read parent context
            context_text = ""
            parent = link.parent
            if parent is not None:
                context_text = parent.get_text(" ", strip=True)
            context_lower = (context_text or "").lower()

            # filter by query tokens
            if query_tokens:
                if not any(t in title_lower or t in context_lower for t in query_tokens):
                    continue

            # normalize url
            href = link["href"]
            url = self._normalize_url(base_url, href)

            # dedupe url
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # build description text
            description = ""
            if context_text and len(context_text) > len(title):
                description = context_text[:300]
            else:
                next_p = link.find_next("p")
                if next_p:
                    description = next_p.get_text(strip=True)[:300]

            # append item dict
            items.append({
                "title": title,
                "url": url,
                "description": description,
                "date": None,
                "source": site_name
            })

            # cap items
            if len(items) >= self.max_results:
                break

        return items

    def _extract_sc_enforcement(
        self,
        html: str,
        base_url: str,
        site_name: str
    ) -> List[Dict[str, Any]]:
        # sc enforcement extraction based on url patterns
        soup = BeautifulSoup(html, "html.parser")

        items: List[Dict[str, Any]] = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            # normalize url
            href = link["href"]
            url = self._normalize_url(base_url, href)
            url_lower = url.lower()

            # filter enforcement urls
            if not any(pattern in url_lower for pattern in (SC_ENFORCEMENT_URL_KEYWORDS or [])):
                continue

            # read title
            title = link.get_text(strip=True)
            if not title:
                continue

            # enforce title length
            if len(title) < 8:
                continue

            # dedupe url
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # read parent context
            context_text = ""
            parent = link.parent
            if parent is not None:
                context_text = parent.get_text(" ", strip=True)

            # build description text
            description = ""
            if context_text and len(context_text) > len(title):
                description = context_text[:300]
            else:
                next_p = link.find_next("p")
                if next_p:
                    description = next_p.get_text(strip=True)[:300]

            # append item dict
            items.append({
                "title": title,
                "url": url,
                "description": description,
                "date": None,
                "source": site_name
            })

            # cap items
            if len(items) >= self.max_results:
                break

        return items

    @component.output_types(documents=List[Document])
    def run(self, query: str) -> Dict[str, Any]:
        # return empty result if no query
        if not query or not query.strip():
            return {"documents": []}

        documents: List[Document] = []
        seen_urls_global = set()

        # build headers
        headers = self._get_headers()

        # encode query
        encoded_query = quote_plus(query.strip())

        # read snippet cap
        snippet_len = int(self.config.SNIPPET_LENGTH)

        with build_httpx_client(
            config=self.config,
            timeout=self.timeout,
            headers=headers,
            follow_redirects=bool(self.config.HTTP_FOLLOW_REDIRECTS),
            verify=resolve_tls_verify(self.config, source_id=self.source_id),
        ) as client:
            for site in self.sites:
                # cap docs
                if len(documents) >= self.max_results:
                    break

                # read site fields
                base_url = site["base_url"]
                search_path = site["search_path"]
                site_name = site["name"]

                # build search url
                search_url = base_url.rstrip("/") + search_path.format(query=encoded_query)

                # fetch search page
                response = client.get(search_url)
                if response.status_code != 200:
                    continue

                # extract items
                if site["id"] == "sc":
                    site_items = self._extract_sc_enforcement(
                        html=response.text,
                        base_url=base_url,
                        site_name=site_name
                    )
                    if not site_items:
                        site_items = self._extract_generic_items(
                            html=response.text,
                            base_url=base_url,
                            site_name=site_name,
                            query=query
                        )
                else:
                    site_items = self._extract_generic_items(
                        html=response.text,
                        base_url=base_url,
                        site_name=site_name,
                        query=query
                    )

                # build documents
                for item in site_items:
                    # read url value
                    url = item["url"]

                    # dedupe url globally
                    if url in seen_urls_global:
                        continue
                    seen_urls_global.add(url)

                    documents.append(
                        create_document(
                            source_name=item["source"],
                            title=item["title"],
                            url=item["url"],
                            snippet=(item["description"] or "")[:snippet_len],
                            content=item["description"] or item["title"],
                            source_date=item["date"]
                        )
                    )

                    # enforce cap
                    if len(documents) >= self.max_results:
                        break

        # log final status
        log_source_status(self.source_id, self.name, len(documents))
        return {"documents": documents}