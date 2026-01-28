"""
load company codes
build bursa urls
parse attachment urls
detect challenge pages
build api urls
load backfill state
save backfill state
parse detail html
build detail text
parse iframe src
detect fileaccess html
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from backend.configuration.bursa_config import (
    BURSA_BASE_URL,
    BURSA_COMPANY_ANNOUNCEMENTS_PATH,
    BURSA_ANNOUNCEMENT_DETAILS_PATH,
    BURSA_API_SEARCH_PATH,
    BURSA_COMPANY_PARAM,
    BURSA_ANN_ID_PARAM,
    BURSA_API_ANN_TYPE_PARAM,
    BURSA_API_ANN_TYPE_VALUE,
    BURSA_API_PER_PAGE_PARAM,
    BURSA_API_PAGE_PARAM,
    BURSA_API_PER_PAGE,
    BURSA_MAX_ATTACHMENT_URLS,
)
from backend.configuration.paths import BURSA_COMPANY_CODES_PATH, BURSA_BACKFILL_STATE_PATH
from backend.helpers.persist.json_utils import load_json, save_json
from backend.helpers.parse.text_helpers import normalize_lookup_key, normalize_spaces, clean_block_text
from backend.helpers.parse.date_helpers import parse_date_to_yyyy_mm_dd, extract_first_date_token


# ==================== CODES ====================

def load_company_codes() -> Dict[str, str]:
    # load company code mapping file
    data = load_json(BURSA_COMPANY_CODES_PATH, default={})
    if not isinstance(data, dict):
        return {}

    # normalize mapping keys and values
    out: Dict[str, str] = {}
    for k, v in data.items():
        # validate key type
        if not isinstance(k, str):
            continue

        # validate value type
        if not isinstance(v, str):
            continue

        # normalize map key
        key = normalize_lookup_key(k)

        # normalize code
        val = normalize_spaces(v)

        # skip empty key
        if not key:
            continue

        # skip empty code
        if not val:
            continue

        # store mapping
        out[key] = val

    return out


def resolve_company_code(query: str, code_map: Dict[str, str]) -> str:
    # resolve company code from query
    raw = normalize_spaces(query)
    if not raw:
        return ""

    # accept direct numeric code
    if raw.isdigit():
        return raw

    # accept code embedded in string
    m = re.search(r"\b(\d{4})\b", raw)
    if m:
        return str(m.group(1))

    # lookup by normalized name
    key = normalize_lookup_key(raw)
    if not key:
        return ""

    # return mapped code
    code = code_map.get(key, "")
    if code:
        return code

    return ""


# ==================== CHALLENGE ====================

def is_challenge_page(html: str) -> bool:
    # detect challenge html
    s = str(html or "").lower()

    # check title marker
    if "<title>just a moment" in s:
        return True

    # check cloudflare platform
    if "cdn-cgi/challenge-platform" in s:
        return True

    # check cf marker
    if "cf_chl_opt" in s:
        return True

    return False


# ==================== URLS ====================

def build_company_announcement_url(company_code: str) -> str:
    # build listing url for company announcements
    base = str(BURSA_BASE_URL).rstrip("/")
    path = str(BURSA_COMPANY_ANNOUNCEMENTS_PATH).lstrip("/")
    url = f"{base}/{path}?{BURSA_COMPANY_PARAM}={company_code}"
    return url


def build_detail_url_from_ann_id(ann_id: str) -> str:
    # build detail url from ann id
    a = str(ann_id or "").strip()
    if not a:
        return ""

    # build detail url
    base = str(BURSA_BASE_URL).rstrip("/")
    path = str(BURSA_ANNOUNCEMENT_DETAILS_PATH).lstrip("/")
    return f"{base}/{path}?{BURSA_ANN_ID_PARAM}={a}"


def normalize_bursa_url(href: str) -> str:
    # normalize relative urls into absolute
    h = str(href or "").strip()
    if not h:
        return ""

    # join with base
    return urljoin(str(BURSA_BASE_URL).rstrip("/") + "/", h)


def build_api_search_url(company_code: str, page: int) -> str:
    # build api search url
    code = str(company_code or "").strip()
    if not code:
        return ""

    # normalize base and path
    base = str(BURSA_BASE_URL).rstrip("/")
    path = str(BURSA_API_SEARCH_PATH).lstrip("/")

    # normalize page size
    per_page = int(BURSA_API_PER_PAGE)
    if per_page <= 0:
        per_page = 20

    # normalize page number
    page_num = int(page)
    if page_num < 1:
        page_num = 1

    # build url with query params
    url = (
        f"{base}/{path}"
        f"?{BURSA_API_ANN_TYPE_PARAM}={BURSA_API_ANN_TYPE_VALUE}"
        f"&{BURSA_COMPANY_PARAM}={code}"
        f"&{BURSA_API_PER_PAGE_PARAM}={per_page}"
        f"&{BURSA_API_PAGE_PARAM}={page_num}"
    )

    return url


# ==================== PARSE ====================

def extract_attachment_urls(detail_html: str, config) -> List[str]:
    # extract pdf like urls from detail html
    html = str(detail_html or "")
    if not html.strip():
        return []

    # read pdf keywords
    keywords = list(getattr(config, "CONTENT_PDF_URL_KEYWORDS", []) or [])

    # parse html
    soup = BeautifulSoup(html, "html.parser")
    found: Set[str] = set()

    for a in soup.find_all("a", href=True):
        # read href
        href = str(a.get("href") or "").strip()
        if not href:
            continue

        # normalize to absolute
        full = normalize_bursa_url(href)
        if not full:
            continue

        # normalize url for checks
        u = full.lower()

        # check pdf suffix
        if u.endswith(".pdf"):
            found.add(full)
        else:
            # check keyword hits
            for k in keywords:
                kk = str(k or "").lower().strip()
                if not kk:
                    continue
                if kk in u:
                    found.add(full)
                    break

        # enforce cap
        if len(found) >= int(BURSA_MAX_ATTACHMENT_URLS):
            break

    return list(found)


# ==================== BACKFILL ====================

def load_bursa_backfill_state() -> Dict[str, Any]:
    # load backfill state json
    data = load_json(BURSA_BACKFILL_STATE_PATH, default={})
    if not isinstance(data, dict):
        return {}
    return data


def save_bursa_backfill_state(state: Dict[str, Any]) -> bool:
    # save backfill state json
    if not isinstance(state, dict):
        return False
    return bool(save_json(BURSA_BACKFILL_STATE_PATH, state))


def get_company_backfill_cursor(state: Dict[str, Any], company_code: str) -> Tuple[int, bool]:
    # get next offset and done flag
    s = state or {}
    code = str(company_code or "").strip()
    if not code:
        return (0, False)

    # read state row
    item = s.get(code)
    if not isinstance(item, dict):
        return (0, False)

    # read cursor values
    next_offset = item.get("next_offset", 0)
    done = bool(item.get("done", False))

    # clamp offset
    off = int(next_offset) if next_offset is not None else 0
    if off < 0:
        off = 0

    return (off, done)


def set_company_backfill_cursor(state: Dict[str, Any], company_code: str, next_offset: int, done: bool) -> Dict[str, Any]:
    # set next offset and done flag
    s = state if isinstance(state, dict) else {}
    code = str(company_code or "").strip()
    if not code:
        return s

    # clamp offset
    off = int(next_offset)
    if off < 0:
        off = 0

    # build updated stamp
    stamp = datetime.now(timezone.utc).isoformat()

    # store state row
    s[code] = {
        "next_offset": int(off),
        "done": bool(done),
        "updated_at": stamp,
    }

    return s


# ==================== IFRAME ====================

def looks_like_bursa_fileaccess_html(html: str) -> bool:
    # detect fileaccess content html
    s = str(html or "").lower()
    if not s.strip():
        return False

    # check main container
    if 'id="main"' in s:
        return True

    # check known blocks
    if "ven_announcement_info" in s:
        return True

    # check company cell
    if "company_name" in s:
        return True

    return False


def extract_fileaccess_iframe_src(html: str, page_url: str) -> str:
    # extract iframe src that points to fileaccess content
    s = str(html or "")
    if not s.strip():
        return ""

    # normalize base url
    base = str(page_url or "").strip()
    soup = BeautifulSoup(s, "html.parser")

    for iframe in soup.find_all("iframe"):
        # read src
        src = str(iframe.get("src") or "").strip()
        if not src:
            continue

        # build absolute
        full = urljoin(base, src) if base else src
        full = str(full).strip()
        if not full:
            continue

        # normalize for checks
        low = full.lower()

        # accept fileaccess patterns
        if "/fileaccess/" in low or "disclosure.bursamalaysia.com" in low:
            return full

    return ""


# ==================== DETAIL ====================

def _cell_text(tag) -> str:
    # read cell text with br
    if tag is None:
        return ""
    text = tag.get_text("\n", strip=True)
    return clean_block_text(text)


def parse_bursa_date_to_yyyy_mm_dd(value: str) -> str:
    # parse bursa date formats
    s = clean_block_text(value)
    if not s:
        return None

    # extract first date token
    token = extract_first_date_token(s)

    # parse token or full string
    parsed = parse_date_to_yyyy_mm_dd(token or s)
    return parsed


def extract_table_as_lines(table) -> List[str]:
    # extract generic table rows
    if table is None:
        return []

    lines: List[str] = []

    # read table rows
    rows = table.find_all("tr")
    for tr in rows:
        # read row cells
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue

        if len(cells) >= 2:
            # read left and right cells
            left = _cell_text(cells[0])
            right = _cell_text(cells[1])

            # skip empty rows
            if not left and not right:
                continue

            # append key value row
            if left and right:
                lines.append(f"{left}: {right}")
            else:
                lines.append(left or right)

            # append extra columns
            if len(cells) > 2:
                extra = []
                for c in cells[2:]:
                    t = _cell_text(c)
                    if not t:
                        continue
                    extra.append(t)
                if extra:
                    lines.append(clean_block_text(" | ".join(extra)))
        else:
            # append single cell row
            t = _cell_text(cells[0])
            if t:
                lines.append(t)

    return lines


def extract_ven_table_as_lines(table) -> List[str]:
    # extract bursa changes table format
    if table is None:
        return []

    lines: List[str] = []

    # read table rows
    rows = table.find_all("tr")
    for tr in rows:
        # read cells
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue

        # normalize cell texts
        texts = [_cell_text(c) for c in cells]
        texts = [t for t in texts if t]

        # skip empty rows
        if not texts:
            continue

        # detect header row
        is_header = any("formTableColumnHeader" in (c.get("class") or []) for c in cells)
        if is_header and len(texts) >= 3:
            lines.append(clean_block_text(" | ".join(texts)))
            continue

        # handle key value rows
        if len(texts) == 2:
            lines.append(f"{texts[0]}: {texts[1]}")
            continue

        # append full row
        lines.append(clean_block_text(" | ".join(texts)))

    return lines


def extract_company_name_from_detail(soup: BeautifulSoup) -> str:
    # extract company name from known cells
    if soup is None:
        return ""

    # read company cell
    td = soup.select_one("td.company_name")
    if td is not None:
        t = _cell_text(td)
        if t:
            return t

    # read announcement info block
    info = soup.select_one("div.ven_announcement_info")
    if info is not None:
        for tr in info.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) >= 2:
                label = _cell_text(tds[0]).lower()
                val = _cell_text(tds[1])
                if "company name" in label and val:
                    return val

    return ""


def extract_title_from_detail(soup: BeautifulSoup) -> str:
    # extract main title from h3
    if soup is None:
        return ""

    # read title node
    h3 = soup.find("h3")
    if h3 is None:
        return ""

    return _cell_text(h3)


def extract_source_date_from_detail(soup: BeautifulSoup) -> str:
    # extract date announced from announcement info
    if soup is None:
        return None

    # read announcement info block
    info = soup.select_one("div.ven_announcement_info")
    if info is None:
        return None

    # scan table rows for date announced
    for tr in info.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2:
            label = _cell_text(tds[0]).lower()
            val = _cell_text(tds[1])
            if "date announced" in label:
                parsed = parse_bursa_date_to_yyyy_mm_dd(val)
                if parsed:
                    return parsed

    return None


def build_bursa_detail_text(detail_html: str) -> Tuple[str, Dict[str, Any]]:
    # build structured text block and extracted meta
    html = str(detail_html or "")
    if not html.strip():
        return ("", {})

    # parse html
    soup = BeautifulSoup(html, "html.parser")

    # strip scripts
    for s in soup.find_all("script"):
        s.decompose()

    # extract known fields
    title = extract_title_from_detail(soup)
    company = extract_company_name_from_detail(soup)
    source_date = extract_source_date_from_detail(soup)

    # scope main content
    main = soup.select_one("#main") or soup

    lines: List[str] = []

    # append top lines
    if title:
        lines.append(title)

    if company:
        lines.append(company)

    # extract section blocks
    h4_list = main.find_all("h4")
    for h4 in h4_list:
        # section label
        header = _cell_text(h4)
        if header:
            lines.append("")
            lines.append(header)

        # scan siblings until next header
        node = h4.find_next_sibling()
        while node is not None and getattr(node, "name", None) not in ["h3", "h4"]:
            name = getattr(node, "name", None)
            if not name:
                node = node.find_next_sibling()
                continue

            # parse tables into lines
            if name == "table":
                cls = " ".join(node.get("class") or []).lower()
                if "ven_table" in cls:
                    lines.extend(extract_ven_table_as_lines(node))
                else:
                    lines.extend(extract_table_as_lines(node))

            node = node.find_next_sibling()

    # join output text
    text = clean_block_text("\n".join(lines))

    # build extracted meta
    meta: Dict[str, Any] = {
        "title_text": title,
        "company_name": company,
        "source_date": source_date,
    }

    return (text, meta)