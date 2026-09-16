"""
marc ratings retriever
extract result links
fetch detail pages
extract rating text
"""

import re
from typing import List, Dict, Any
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from haystack.core.component import component
from haystack.dataclasses import Document

from backend.configuration.sources import (
    MARC_RATINGS_BASE_URL,
    MARC_RATINGS_SEARCH_URL_TEMPLATE,
    MARC_RATINGS_MAX_RESULTS,
    MARC_RATINGS_QUERY_TOKEN_MIN_LENGTH,
    MARC_RATINGS_MIN_QUERY_MATCHES,
    MARC_RATINGS_ALLOW_PREFIX_MATCH,
    MARC_RATINGS_DROP_QUERY_TOKENS,
    USER_AGENT,
)
from backend.helpers.fetch.httpx_helpers import build_httpx_client, resolve_tls_verify
from backend.helpers.fetch.source_helpers import create_document, log_source_status
from backend.helpers.parse.text_helpers import clean_block_text


# ==================== MARC RATINGS RETRIEVER ====================

@component
class MARCRatingsRetriever:

    def __init__(self, config):
        # store config and ids
        self.config = config
        self.source_id = "marc_ratings"
        self.name = "MARC Ratings"

        # load timeouts and limits
        self.timeout = int(config.SOURCE_DEFAULT_TIMEOUT)
        self.max_results = int(MARC_RATINGS_MAX_RESULTS)

        # store urls
        self.base_url = str(MARC_RATINGS_BASE_URL).rstrip("/")
        self.search_template = str(MARC_RATINGS_SEARCH_URL_TEMPLATE)

        # print init status
        print(f"[SOURCE] {self.source_id} ({self.name}) initialized")

    def _get_headers(self) -> Dict[str, str]:
        # build basic headers
        return {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _extract_result_links(self, html: str) -> List[str]:
        # extract result links from elementor card headings
        soup = BeautifulSoup(str(html or ""), "html.parser")
        found: List[str] = []
        seen = set()

        # select card links
        anchors = soup.select("article h4.elementor-heading-title a[href]")
        if not anchors:
            anchors = soup.select("h4.elementor-heading-title a[href]")

        for a in anchors:
            # read href
            href = str(a.get("href") or "").strip()
            if not href:
                continue

            # build absolute url
            full = urljoin(self.base_url + "/", href)
            low = full.lower()

            # keep site urls only
            if "marc.com.my" not in low:
                continue

            # focus rating announcements
            if "/rating-announcements/" not in low and "/rating-announcement/" not in low:
                continue

            # dedupe url
            key = low
            if key in seen:
                continue
            seen.add(key)
            found.append(full)

            # enforce cap
            if len(found) >= (self.max_results * 3):
                break

        return found

    def _extract_article_content(self, html: str) -> Dict[str, Any]:
        # parse title and content from marc html
        soup = BeautifulSoup(str(html or ""), "html.parser")

        # read title from og tags
        title = ""
        og = soup.select_one("meta[property='og:title']")
        if og is not None:
            title = clean_block_text(str(og.get("content") or ""))

        # fallback to h1
        if not title:
            h1 = soup.find("h1")
            title = clean_block_text(h1.get_text(" ", strip=True) if h1 else "")

        # fallback to title tag
        if not title:
            t = soup.find("title")
            title = clean_block_text(t.get_text(" ", strip=True) if t else "")

        # collect candidate blocks
        blocks = []
        blocks.extend(soup.select("div.elementor-widget-container"))
        blocks.extend(soup.select("div.entry-content"))

        parts: List[str] = []
        for blk in blocks:
            # read paragraph tags
            for p in blk.find_all("p"):
                text = clean_block_text(p.get_text(" ", strip=True))
                if not text:
                    continue
                parts.append(text)

        # dedupe paragraphs
        out_parts: List[str] = []
        seen = set()
        for t in parts:
            # dedupe by lower text
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out_parts.append(t)

        # join paragraphs
        content = clean_block_text("\n\n".join(out_parts))

        return {
            "title": title,
            "content": content,
            "source_date": None,
        }

    def _looks_like_rating_note(self, content: str) -> bool:
        # filter for rating related text
        s = str(content or "")
        low = s.lower()
        if not low.strip():
            return False

        # match site marker
        if "marc ratings" in low:
            return True

        # match marc dash rating
        if re.search(r"\bmarc-\d\b", low):
            return True

        # match marc 1 token
        if re.search(r"\bmarc[-\s]?1\b", low):
            return True

        # match rating keyword
        if re.search(r"\baaa\b", low) and "rating" in low:
            return True

        # match content sections
        if "financial institution ratings" in low:
            return True

        # match withdrawn mention
        if "withdrawn" in low and "ratings" in low:
            return True

        return False

    def _build_query_tokens(self, query: str) -> List[str]:
        # build query tokens list
        q = str(query or "").lower().strip()
        if not q:
            return []

        # read token length
        min_len = int(MARC_RATINGS_QUERY_TOKEN_MIN_LENGTH)

        # extract tokens
        tokens = re.findall(rf"[a-z0-9]{{{min_len},}}", q)

        # build drop set
        drop = set(
            str(x or "").lower().strip()
            for x in (MARC_RATINGS_DROP_QUERY_TOKENS or [])
            if str(x or "").strip()
        )

        out: List[str] = []
        seen = set()

        for tok in tokens:
            # skip dropped token
            if tok in drop:
                continue

            # dedupe token
            if tok in seen:
                continue

            # store token
            seen.add(tok)
            out.append(tok)

        return out

    def _matches_query_tokens(self, query: str, title: str, content: str) -> bool:
        # match query tokens with flexible rules
        q = str(query or "").lower().strip()
        if not q:
            return True

        # build match text
        text = f"{title} {content}".lower()

        # accept full phrase match
        if q and q in text:
            return True

        # build tokens
        tokens = self._build_query_tokens(q)
        if not tokens:
            return True

        # read match rules
        min_matches = int(MARC_RATINGS_MIN_QUERY_MATCHES)
        allow_prefix = bool(MARC_RATINGS_ALLOW_PREFIX_MATCH)

        matches = 0
        for tok in tokens:
            # match token with boundary
            if allow_prefix:
                ok = bool(re.search(rf"\b{re.escape(tok)}\w*\b", text))
            else:
                ok = bool(re.search(rf"\b{re.escape(tok)}\b", text))

            # increment match count
            if ok:
                matches += 1

        return matches >= min_matches

    @component.output_types(documents=List[Document])
    def run(self, query: str) -> Dict[str, Any]:
        # run marc ratings retrieval
        q = str(query or "").strip()
        if not q:
            log_source_status(self.source_id, self.name, 0, "empty query")
            return {"documents": []}

        # build search url
        encoded = quote_plus(q)
        search_url = self.search_template.format(query=encoded)

        # build request headers
        headers = self._get_headers()

        # read tls flag
        verify = resolve_tls_verify(self.config, source_id=self.source_id)

        documents: List[Document] = []

        # read clamps
        snippet_len = int(self.config.SNIPPET_LENGTH)
        min_len = int(self.config.DATABASE_MIN_CONTENT_LENGTH)

        with build_httpx_client(
            config=self.config,
            timeout=self.timeout,
            headers=headers,
            follow_redirects=bool(self.config.HTTP_FOLLOW_REDIRECTS),
            verify=verify,
        ) as client:
            # fetch search page
            r = client.get(search_url)
            if int(r.status_code) != 200:
                log_source_status(self.source_id, self.name, 0, f"status={r.status_code}")
                return {"documents": []}

            # parse result links
            links = self._extract_result_links(r.text)

            # fetch each result url
            for url in links:
                # fetch detail page
                rr = client.get(url)
                if int(rr.status_code) != 200:
                    continue

                # parse html into fields
                parsed = self._extract_article_content(rr.text)
                title = str(parsed.get("title") or "").strip()
                content = str(parsed.get("content") or "").strip()

                # skip empty content
                if not content:
                    continue

                # filter rating notes
                if not self._looks_like_rating_note(content):
                    continue

                # require query match
                if not self._matches_query_tokens(q, title, content):
                    continue

                # skip short content
                if len(content) < min_len:
                    continue

                # append document row
                documents.append(
                    create_document(
                        source_name=self.name,
                        title=title or "marc rating note",
                        url=url,
                        snippet=content[:snippet_len],
                        content=content,
                        source_date=None,
                    )
                )

                # enforce cap
                if len(documents) >= self.max_results:
                    break

        # log status
        log_source_status(self.source_id, self.name, len(documents))

        return {"documents": documents}