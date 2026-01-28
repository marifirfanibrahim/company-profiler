"""
extract full article content from urls
use trafilatura for clean content extraction
extract publication date from content
"""

import concurrent.futures
from typing import List, Dict, Any

from haystack.core.component import component
from haystack.dataclasses import Document

import trafilatura
from bs4 import BeautifulSoup

from backend.configuration.sources import USER_AGENT
from backend.helpers.parse.pdf_utils import extract_pdf_text_from_bytes
from backend.helpers.parse.ocr_helpers import ocr_from_html_images
from backend.helpers.fetch.httpx_helpers import build_httpx_client
from backend.helpers.parse.date_helpers import (
    DATE_PATTERNS,
    parse_yyyy_mm_dd,
    parse_date_to_yyyy_mm_dd,
    extract_first_date_token,
)


# ==================== CONTENT EXTRACTOR COMPONENT ====================

@component
class ContentExtractor:

    def __init__(self, config):
        # store config reference
        self.config = config

        # load settings from config
        self.max_docs = int(config.CONTENT_EXTRACT_MAX_DOCS)
        self.timeout = int(config.CONTENT_EXTRACT_TIMEOUT)
        self.min_length = int(config.MIN_CONTENT_LENGTH)
        self.workers = int(config.CONTENT_EXTRACT_WORKERS)

        # load domains to skip
        self.skip_domains = list(config.CONTENT_SKIP_DOMAINS)

        # print init message
        print(f"[CONTENT] Trafilatura extractor initialized (max: {self.max_docs})")

    def _get_headers(self) -> Dict[str, str]:
        # return headers
        return {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _extract_date(self, html: str, content: str) -> str:
        # try extract date from html or content
        metadata = trafilatura.extract_metadata(html)
        if metadata and getattr(metadata, "date", None):
            # normalize metadata date
            raw = str(metadata.date or "").strip()
            raw = raw[:10]

            # parse ymd date
            parsed = parse_yyyy_mm_dd(raw)
            if parsed:
                return parsed

        # parse html for meta tags
        soup = BeautifulSoup(html, "html.parser")

        date_metas = [
            ("property", "article:published_time"),
            ("property", "og:published_time"),
            ("name", "pubdate"),
            ("name", "publishdate"),
            ("name", "date"),
            ("itemprop", "datePublished"),
        ]

        for attr, value in date_metas:
            # read matching meta tag
            tag = soup.find("meta", {attr: value})
            if tag and tag.get("content"):
                # normalize date value
                date_str = str(tag["content"] or "")[:10]

                # parse ymd date
                parsed = parse_yyyy_mm_dd(date_str)
                if parsed:
                    return parsed

        # read time datetime value
        time_tag = soup.find("time", {"datetime": True})
        if time_tag:
            # normalize date value
            date_str = str(time_tag["datetime"] or "")[:10]

            # parse ymd date
            parsed = parse_yyyy_mm_dd(date_str)
            if parsed:
                return parsed

        # clamp search window
        date_search_chars = int(self.config.CONTENT_DATE_SEARCH_CHARS)
        text_to_search = (content or "")[:date_search_chars]

        # extract first token
        token = extract_first_date_token(text_to_search, patterns=DATE_PATTERNS)
        if token:
            # parse token with multi format parser
            parsed = parse_date_to_yyyy_mm_dd(token)
            if parsed:
                return parsed

        return None

    def _is_pdf_response(self, url: str, headers: dict) -> bool:
        # detect pdf response
        u = str(url or "").lower()
        ct = str((headers or {}).get("content-type", "") or "").lower()

        # detect content type
        if "application/pdf" in ct:
            return True

        # detect url suffix
        if u.endswith(".pdf"):
            return True

        # detect keyword match
        for key in list(self.config.CONTENT_PDF_URL_KEYWORDS):
            k = str(key or "").lower().strip()
            if not k:
                continue
            if k in u:
                return True

        return False

    def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        # extract text from pdf bytes
        if not bool(self.config.PDF_EXTRACT_ENABLED):
            return ""

        # read pdf settings
        max_pages = int(self.config.PDF_EXTRACT_MAX_PAGES)
        max_chars = int(self.config.PDF_EXTRACT_MAX_CHARS)
        joiner = str(self.config.PDF_EXTRACT_JOIN)

        return extract_pdf_text_from_bytes(
            pdf_bytes=pdf_bytes,
            max_pages=max_pages,
            max_chars=max_chars,
            joiner=joiner,
        )

    def _fetch_url(self, url: str, headers: Dict[str, str]):
        # fetch url using httpx
        with build_httpx_client(
            config=self.config,
            timeout=self.timeout,
            headers=headers,
            follow_redirects=bool(self.config.HTTP_FOLLOW_REDIRECTS),
            verify=bool(self.config.HTTP_VERIFY_TLS),
        ) as client:
            # run request
            return client.get(url)

    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document], max_docs: int = None) -> Dict[str, Any]:
        # return empty if no documents
        if not documents:
            return {"documents": []}

        # select max docs
        if max_docs is None:
            cap = self.max_docs
        else:
            cap = int(max_docs)

        # clamp input documents
        docs_to_process = documents[:cap]

        # store output documents
        enriched = []

        # track fetch count
        fetch_count = 0

        # build request headers
        headers = self._get_headers()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            for doc in docs_to_process:
                # read url meta
                url = doc.meta.get("url", "")

                # keep docs without url
                if not url or url == "#":
                    enriched.append(doc)
                    continue

                # apply skip domains
                lowered = url.lower()
                if any(domain in lowered for domain in self.skip_domains):
                    enriched.append(doc)
                    continue

                # skip docs with long content
                existing_threshold = int(self.config.CONTENT_EXISTING_THRESHOLD)
                if len(doc.content) > existing_threshold:
                    enriched.append(doc)
                    continue

                # schedule fetch task
                future = executor.submit(self._fetch_url, url, headers)

                # handle future error state
                exc = future.exception()
                if exc is not None:
                    enriched.append(doc)
                    continue

                # read response
                response = future.result()
                if response.status_code != 200:
                    enriched.append(doc)
                    continue

                # detect pdf response
                is_pdf = self._is_pdf_response(url, dict(response.headers))

                if is_pdf:
                    # extract pdf text
                    pdf_text = self._extract_pdf_text(response.content)

                    # read pdf min length
                    pdf_min = int(self.config.PDF_MIN_CONTENT_LENGTH)

                    if pdf_text and len(pdf_text) >= pdf_min:
                        # read truncation values
                        snippet_len = int(self.config.SNIPPET_LENGTH)
                        max_extract = int(self.config.CONTENT_MAX_EXTRACT_CHARS)

                        # build snippet and content
                        snippet = pdf_text[:snippet_len].strip()
                        content = pdf_text[:max_extract].strip()

                        enriched.append(
                            Document(
                                content=content,
                                meta={
                                    **doc.meta,
                                    "snippet": snippet,
                                },
                            )
                        )
                        fetch_count += 1
                        continue

                    enriched.append(doc)
                    continue

                # read html text
                html = response.text

                # extract main content
                content = trafilatura.extract(
                    html,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=True,
                    favor_precision=True,
                )

                # read source date
                source_date = doc.meta.get("source_date")
                if not source_date:
                    source_date = self._extract_date(html, content)

                # track ocr usage
                ocr_used = False

                if bool(self.config.OCR_ENABLED):
                    # read ocr threshold
                    min_ocr_len = int(self.config.OCR_MIN_TEXT_LENGTH)

                    # read current text length
                    current_len = len(content or "")
                    if current_len < min_ocr_len:
                        # run ocr extraction
                        ocr_text = ocr_from_html_images(
                            html=html,
                            page_url=url,
                            config=self.config,
                            headers=headers,
                        )

                        # merge ocr text
                        if ocr_text and len(ocr_text) >= min_ocr_len:
                            if content:
                                content = f"{content}\n\n{ocr_text}".strip()
                            else:
                                content = ocr_text.strip()
                            ocr_used = True

                if content and len(content) >= self.min_length:
                    # read truncation values
                    max_extract = int(self.config.CONTENT_MAX_EXTRACT_CHARS)
                    snippet_len = int(self.config.SNIPPET_LENGTH)

                    # clamp extracted text
                    content2 = str(content or "")[:max_extract].strip()

                    # build snippet
                    snippet = content2[:snippet_len].strip()

                    enriched.append(
                        Document(
                            content=content2,
                            meta={
                                **doc.meta,
                                "snippet": snippet,
                                "ocr_used": bool(ocr_used),
                                "source_date": source_date,
                            },
                        )
                    )
                    fetch_count += 1
                    continue

                # store date only update
                if source_date and not doc.meta.get("source_date"):
                    enriched.append(
                        Document(
                            content=doc.content,
                            meta={**doc.meta, "source_date": source_date},
                        )
                    )
                else:
                    enriched.append(doc)

        # print fetch status
        if fetch_count:
            print(f"[CONTENT] Extracted {fetch_count}/{len(docs_to_process)} documents")

        return {"documents": enriched}