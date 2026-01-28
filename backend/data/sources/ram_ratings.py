"""
ram ratings retriever
fetch list fragments
fetch detail pages
extract rating text
"""

from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup
from haystack.core.component import component
from haystack.dataclasses import Document

from backend.configuration.sources import (
    RAM_RATINGS_BASE_URL,
    RAM_RATINGS_MAX_RESULTS,
    RAM_RATINGS_SCRIPT_PATH,
    RAM_RATINGS_SCRIPT_HTML_PARAM,
    RAM_RATINGS_SCRIPT_OSP,
    RAM_RATINGS_SCRIPT_TYPE,
    RAM_RATINGS_SCRIPT_CATID,
    RAM_RATINGS_SCRIPT_PAGE_PARAM,
    RAM_RATINGS_SCRIPT_SEARCH_PARAM,
    RAM_RATINGS_SCRIPT_OSPTYPE_PARAM,
    RAM_RATINGS_SCRIPT_MAX_PAGES,
    RAM_RATINGS_SCRIPT_OSPTYPES,
    USER_AGENT,
)
from backend.helpers.fetch.httpx_helpers import build_httpx_client
from backend.helpers.fetch.source_helpers import create_document, log_source_status
from backend.helpers.parse.text_helpers import clean_block_text
from backend.helpers.parse.date_helpers import extract_first_date_token, parse_date_to_yyyy_mm_dd


# ==================== RAM RATINGS RETRIEVER ====================

@component
class RAMRatingsRetriever:

    def __init__(self, config):
        # store config and ids
        self.config = config
        self.source_id = "ram_ratings"
        self.name = "RAM Ratings"

        # load timeouts and limits
        self.timeout = int(config.SOURCE_DEFAULT_TIMEOUT)
        self.max_results = int(RAM_RATINGS_MAX_RESULTS)

        # store base url
        self.base_url = str(RAM_RATINGS_BASE_URL).rstrip("/")

        # store script settings
        self.script_path = str(RAM_RATINGS_SCRIPT_PATH).strip()
        self.script_html_param = str(RAM_RATINGS_SCRIPT_HTML_PARAM).strip()
        self.script_osp = int(RAM_RATINGS_SCRIPT_OSP)
        self.script_type = str(RAM_RATINGS_SCRIPT_TYPE).strip()
        self.script_catid = int(RAM_RATINGS_SCRIPT_CATID)
        self.script_page_param = str(RAM_RATINGS_SCRIPT_PAGE_PARAM).strip()
        self.script_search_param = str(RAM_RATINGS_SCRIPT_SEARCH_PARAM).strip()
        self.script_osptype_param = str(RAM_RATINGS_SCRIPT_OSPTYPE_PARAM).strip()
        self.script_max_pages = int(RAM_RATINGS_SCRIPT_MAX_PAGES)
        self.script_osptypes = list(RAM_RATINGS_SCRIPT_OSPTYPES)

        # print init status
        print(f"[SOURCE] {self.source_id} ({self.name}) initialized")

    def _get_headers(self) -> Dict[str, str]:
        # build basic headers
        return {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _build_script_url(self) -> str:
        # build script url
        base = self.base_url.rstrip("/")
        path = str(self.script_path).strip()

        # normalize leading slash
        if not path.startswith("/"):
            path = "/" + path

        return f"{base}{path}"

    def _fetch_script_fragment(self, client, osptype: str, page: int, query: str) -> str:
        # fetch html fragment from script endpoint
        params: Dict[str, Any] = {}

        # include html param
        params[self.script_html_param] = ""

        # include script params
        params["osp"] = int(self.script_osp)
        params["type"] = str(self.script_type)
        params["catid"] = int(self.script_catid)
        params[self.script_osptype_param] = str(osptype)
        params[self.script_page_param] = int(page)
        params[self.script_search_param] = str(query)

        # run request
        url = self._build_script_url()
        r = client.get(url, params=params)

        # validate status
        if int(r.status_code) != 200:
            return ""

        return str(r.text or "")

    def _extract_list_items(self, html: str) -> List[Dict[str, Any]]:
        # extract list items from fragment html
        soup = BeautifulSoup(str(html or ""), "html.parser")

        items: List[Dict[str, Any]] = []

        for li in soup.find_all("li"):
            # read title link
            title_a = li.select_one("div.title a[href]")
            href = str(title_a.get("href") or "").strip() if title_a else ""
            title = clean_block_text(title_a.get_text(" ", strip=True) if title_a else "")

            # skip invalid rows
            if not href or not title:
                continue

            # read date text
            em = li.select_one("div.summary em")
            em_text = clean_block_text(em.get_text(" ", strip=True) if em else "")
            date_token = extract_first_date_token(em_text)
            source_date = parse_date_to_yyyy_mm_dd(date_token) if date_token else None

            # read snippet text
            snippet = ""
            summary = li.select_one("div.summary")
            if summary is not None:
                spans = summary.find_all("span")
                texts = []
                for sp in spans:
                    # read span text
                    t = clean_block_text(sp.get_text(" ", strip=True))
                    if not t:
                        continue
                    if t == "-":
                        continue
                    texts.append(t)
                if texts:
                    snippet = texts[-1]

            # build absolute url
            full_url = urljoin(self.base_url + "/", href)

            items.append(
                {
                    "title": title,
                    "url": full_url,
                    "snippet": snippet,
                    "source_date": source_date,
                }
            )

        return items

    def _extract_prviewid_from_url(self, url: str) -> str:
        # extract prviewid from url query string
        u = str(url or "").strip()
        if not u:
            return ""

        # parse query string
        parsed = urlparse(u)
        qs = parse_qs(parsed.query or "")

        # read prviewid variants
        pid_list = qs.get("prviewid") or qs.get("prviewId") or qs.get("prviewID") or []
        if not pid_list:
            return ""

        # normalize id
        pid = str(pid_list[0] or "").strip()
        if not pid.isdigit():
            return ""

        return pid

    def _build_pressrelease_url(self, prviewid: str) -> str:
        # build pressrelease url from id
        pid = str(prviewid or "").strip()
        if not pid:
            return ""
        return f"{self.base_url}/pressrelease/?prviewid={pid}"

    def _extract_pressrelease_content(self, html: str) -> Dict[str, Any]:
        # parse title date and content from pressrelease html
        soup = BeautifulSoup(str(html or ""), "html.parser")

        # locate content container
        container = soup.select_one("div.container.align-left")
        if container is None:
            container = soup

        # read title
        h1 = container.select_one("h1.page-title") or container.find("h1")
        title = clean_block_text(h1.get_text(" ", strip=True) if h1 else "")

        # read published date
        published_text = ""
        em = container.find("em")
        if em is not None:
            published_text = clean_block_text(em.get_text(" ", strip=True))
        date_token = extract_first_date_token(published_text)
        source_date = parse_date_to_yyyy_mm_dd(date_token) if date_token else None

        parts: List[str] = []
        for p in container.find_all("p"):
            # skip social wrapper
            cls = " ".join(p.get("class") or []).lower()
            if "wrapper_social" in cls:
                continue

            # read text
            text = clean_block_text(p.get_text(" ", strip=True))
            if not text:
                continue

            # skip disclaimer blocks
            low = text.lower()
            if "ram ratings receives compensation" in low:
                continue
            if "the credit rating is not a recommendation" in low:
                continue

            parts.append(text)

        # join paragraph text
        content = clean_block_text("\n\n".join(parts))

        return {
            "title": title,
            "source_date": source_date,
            "content": content,
        }

    def _fetch_pressrelease_document(self, client, prviewid: str) -> Document:
        # fetch pressrelease and return document
        url = self._build_pressrelease_url(prviewid)
        if not url:
            return None

        # fetch url
        r = client.get(url)
        if int(r.status_code) != 200:
            return None

        # parse html into fields
        parsed = self._extract_pressrelease_content(r.text)
        title = str(parsed.get("title") or "").strip()
        source_date = parsed.get("source_date")
        content = str(parsed.get("content") or "").strip()

        # skip empty content
        if not content:
            return None

        # read snippet len
        snippet_len = int(self.config.SNIPPET_LENGTH)

        return create_document(
            source_name=self.name,
            title=title or "ram item",
            url=url,
            snippet=content[:snippet_len],
            content=content,
            source_date=source_date,
        )

    @component.output_types(documents=List[Document])
    def run(self, query: str) -> Dict[str, Any]:
        # run ram ratings retrieval
        q = str(query or "").strip()
        if not q:
            log_source_status(self.source_id, self.name, 0, "empty query")
            return {"documents": []}

        # build request headers
        headers = self._get_headers()

        # read tls flag
        verify = bool(self.config.HTTP_VERIFY_TLS)

        documents: List[Document] = []
        seen_urls = set()
        seen_pr = set()

        # read tab list
        max_pages = int(self.script_max_pages)
        osptypes = list(self.script_osptypes)

        with build_httpx_client(
            config=self.config,
            timeout=self.timeout,
            headers=headers,
            follow_redirects=bool(self.config.HTTP_FOLLOW_REDIRECTS),
            verify=verify,
        ) as client:
            for osptype in osptypes:
                # stop on cap
                if len(documents) >= self.max_results:
                    break

                # fetch pages for tab
                for page in range(0, max_pages):
                    # stop on cap
                    if len(documents) >= self.max_results:
                        break

                    # fetch fragment html
                    fragment = self._fetch_script_fragment(
                        client=client,
                        osptype=osptype,
                        page=page,
                        query=q,
                    )

                    # stop on empty fragment
                    if not fragment.strip():
                        break

                    # parse list items
                    items = self._extract_list_items(fragment)
                    if not items:
                        break

                    for item in items:
                        # stop on cap
                        if len(documents) >= self.max_results:
                            break

                        # read fields
                        url = str(item.get("url") or "").strip()
                        title = str(item.get("title") or "").strip()
                        snippet = str(item.get("snippet") or "").strip()
                        source_date = item.get("source_date")

                        # skip url duplicates
                        if not url or url in seen_urls:
                            continue

                        # track url
                        seen_urls.add(url)

                        # check pressrelease id
                        pid = self._extract_prviewid_from_url(url)
                        if pid:
                            # skip pid duplicates
                            if pid in seen_pr:
                                continue

                            # track pid
                            seen_pr.add(pid)

                            # fetch detail doc
                            doc = self._fetch_pressrelease_document(client=client, prviewid=pid)
                            if doc:
                                documents.append(doc)
                            continue

                        # read snippet len
                        snippet_len = int(self.config.SNIPPET_LENGTH)

                        # append placeholder doc
                        documents.append(
                            create_document(
                                source_name=self.name,
                                title=title,
                                url=url,
                                snippet=(snippet or "")[:snippet_len],
                                content="",
                                source_date=source_date,
                            )
                        )

        # log status
        log_source_status(self.source_id, self.name, len(documents))

        return {"documents": documents}