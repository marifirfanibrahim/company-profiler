"""
fetch helpers
build clients
run retrieval
build queries
"""

from .httpx_helpers import build_httpx_client
from .selenium_helpers import (
    build_chrome_driver,
    fetch_page_source,
    wait_for_css,
    scroll_to_bottom,
    click_first_xpath,
    dismiss_common_overlays,
    has_cookie,
)
from .source_helpers import (
    extract_query_words,
    has_any_query_word,
    clean_html,
    create_document,
    log_results,
    log_source_status,
)
from .query_helpers import (
    normalize_query,
    dedupe_queries,
    build_expanded_queries,
)
from .bursa_helpers import (
    load_company_codes,
    resolve_company_code,
    is_challenge_page,
    build_company_announcement_url,
    build_detail_url_from_ann_id,
    normalize_bursa_url,
    build_api_search_url,
    extract_attachment_urls,
    load_bursa_backfill_state,
    save_bursa_backfill_state,
    get_company_backfill_cursor,
    set_company_backfill_cursor,
    looks_like_bursa_fileaccess_html,
    extract_fileaccess_iframe_src,
    parse_bursa_date_to_yyyy_mm_dd,
    extract_table_as_lines,
    extract_ven_table_as_lines,
    extract_company_name_from_detail,
    extract_title_from_detail,
    extract_source_date_from_detail,
    build_bursa_detail_text,
)

# export list
__all__ = [
    "build_httpx_client",
    "build_chrome_driver",
    "fetch_page_source",
    "wait_for_css",
    "scroll_to_bottom",
    "click_first_xpath",
    "dismiss_common_overlays",
    "has_cookie",
    "extract_query_words",
    "has_any_query_word",
    "clean_html",
    "create_document",
    "log_results",
    "log_source_status",
    "normalize_query",
    "dedupe_queries",
    "build_expanded_queries",
    "load_company_codes",
    "resolve_company_code",
    "is_challenge_page",
    "build_company_announcement_url",
    "build_detail_url_from_ann_id",
    "normalize_bursa_url",
    "build_api_search_url",
    "extract_attachment_urls",
    "load_bursa_backfill_state",
    "save_bursa_backfill_state",
    "get_company_backfill_cursor",
    "set_company_backfill_cursor",
    "looks_like_bursa_fileaccess_html",
    "extract_fileaccess_iframe_src",
    "parse_bursa_date_to_yyyy_mm_dd",
    "extract_table_as_lines",
    "extract_ven_table_as_lines",
    "extract_company_name_from_detail",
    "extract_title_from_detail",
    "extract_source_date_from_detail",
    "build_bursa_detail_text",
]