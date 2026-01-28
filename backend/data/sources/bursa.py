"""
bursa retriever
use selenium session
call bursa api endpoint
extract announcement ids
extract attachment urls
backfill results by offset
follow fileaccess iframe
return detail text only
"""

import re
import time
from typing import List, Dict, Any, Tuple

from haystack.core.component import component
from haystack.dataclasses import Document

from backend.configuration.bursa_config import (
    BURSA_MAX_RESULTS,
    BURSA_API_MAX_PAGES,
    BURSA_API_PER_PAGE,
    BURSA_SELENIUM_HEADLESS,
    BURSA_SELENIUM_PAGE_LOAD_TIMEOUT,
    BURSA_SELENIUM_PAGE_LOAD_STRATEGY,
    BURSA_SELENIUM_WAIT_SECONDS,
    BURSA_SELENIUM_WAIT_POLL_SECONDS,
    BURSA_SELENIUM_LISTING_WAIT_CSS,
    BURSA_SELENIUM_DETAIL_WAIT_CSS,
    BURSA_SELENIUM_WINDOW_WIDTH,
    BURSA_SELENIUM_WINDOW_HEIGHT,
    BURSA_SELENIUM_SCROLL_ENABLED,
    BURSA_SELENIUM_SCROLL_STEPS,
    BURSA_SELENIUM_SCROLL_SLEEP_SECONDS,
    BURSA_SELENIUM_USE_PROFILE,
    BURSA_SELENIUM_USER_DATA_DIR,
    BURSA_SELENIUM_PROFILE_DIR,
    BURSA_SELENIUM_CHROME_ARGS,
    BURSA_CHALLENGE_WAIT_SECONDS,
    BURSA_CHALLENGE_POLL_SECONDS,
    BURSA_CHALLENGE_SUCCESS_COOKIE,
    BURSA_CHALLENGE_SUCCESS_SUBSTRING,
    BURSA_BACKFILL_ENABLED,
    BURSA_BACKFILL_PAGES_PER_RUN,
    BURSA_BACKFILL_AFTER_DONE_PAGES_PER_RUN,
    BURSA_BACKFILL_RESET_OFFSET_ON_DONE,
)
from backend.helpers.fetch.source_helpers import create_document, log_source_status
from backend.helpers.fetch.bursa_helpers import (
    load_company_codes,
    resolve_company_code,
    build_company_announcement_url,
    build_api_search_url,
    build_detail_url_from_ann_id,
    extract_attachment_urls,
    is_challenge_page,
    load_bursa_backfill_state,
    save_bursa_backfill_state,
    get_company_backfill_cursor,
    set_company_backfill_cursor,
    build_bursa_detail_text,
    looks_like_bursa_fileaccess_html,
    extract_fileaccess_iframe_src,
)
from backend.helpers.fetch.selenium_helpers import (
    build_chrome_driver,
    fetch_page_source,
    wait_for_css,
    scroll_to_bottom,
    dismiss_common_overlays,
    has_cookie,
)


# ==================== BURSA RETRIEVER ====================

@component
class BursaRetriever:

    def __init__(self, config):
        # store config reference
        self.config = config

        # store ids
        self.source_id = "bursa"
        self.name = "Bursa Disclosure"

        # load limits
        self.max_results = int(BURSA_MAX_RESULTS)
        self.api_max_pages = int(BURSA_API_MAX_PAGES)

        # load api paging
        self.per_page = int(BURSA_API_PER_PAGE)

        # load backfill config
        self.backfill_enabled = bool(BURSA_BACKFILL_ENABLED)
        self.backfill_pages_per_run = int(BURSA_BACKFILL_PAGES_PER_RUN)
        self.backfill_after_done_pages_per_run = int(BURSA_BACKFILL_AFTER_DONE_PAGES_PER_RUN)
        self.backfill_reset_offset_on_done = bool(BURSA_BACKFILL_RESET_OFFSET_ON_DONE)

        # load selenium config
        self.headless = bool(BURSA_SELENIUM_HEADLESS)
        self.page_load_timeout = int(BURSA_SELENIUM_PAGE_LOAD_TIMEOUT)
        self.page_load_strategy = str(BURSA_SELENIUM_PAGE_LOAD_STRATEGY or "").strip()
        self.wait_seconds = int(BURSA_SELENIUM_WAIT_SECONDS)
        self.wait_poll_seconds = float(BURSA_SELENIUM_WAIT_POLL_SECONDS)
        self.listing_wait_css = str(BURSA_SELENIUM_LISTING_WAIT_CSS or "").strip()
        self.detail_wait_css = str(BURSA_SELENIUM_DETAIL_WAIT_CSS or "").strip()
        self.window_width = int(BURSA_SELENIUM_WINDOW_WIDTH)
        self.window_height = int(BURSA_SELENIUM_WINDOW_HEIGHT)
        self.scroll_enabled = bool(BURSA_SELENIUM_SCROLL_ENABLED)
        self.scroll_steps = int(BURSA_SELENIUM_SCROLL_STEPS)
        self.scroll_sleep = float(BURSA_SELENIUM_SCROLL_SLEEP_SECONDS)
        self.use_profile = bool(BURSA_SELENIUM_USE_PROFILE)
        self.user_data_dir = str(BURSA_SELENIUM_USER_DATA_DIR or "").strip()
        self.profile_dir = str(BURSA_SELENIUM_PROFILE_DIR or "").strip()
        self.chrome_args = list(BURSA_SELENIUM_CHROME_ARGS or [])

        # challenge wait
        self.challenge_wait = int(BURSA_CHALLENGE_WAIT_SECONDS)
        self.challenge_poll = float(BURSA_CHALLENGE_POLL_SECONDS)
        self.challenge_cookie = str(BURSA_CHALLENGE_SUCCESS_COOKIE or "").strip()
        self.challenge_substring = str(BURSA_CHALLENGE_SUCCESS_SUBSTRING or "").strip()

        # load company code map
        self.code_map = load_company_codes()

        # print init status
        print(f"[SOURCE] {self.source_id} ({self.name}) initialized")

    def _extract_ann_ids_from_text(self, text: str) -> List[str]:
        # extract ann ids from text using regex
        s = str(text or "")
        if not s.strip():
            return []

        # extract ids from query params
        ids = re.findall(r"\bann_id=(\d+)\b", s)
        if not ids:
            return []

        out = []
        seen = set()
        for ann_id in ids:
            # normalize id
            a = str(ann_id or "").strip()
            if not a:
                continue

            # dedupe id
            if a in seen:
                continue

            # store id
            seen.add(a)
            out.append(a)

        return out

    def _challenge_cleared(self, driver) -> bool:
        # detect cleared challenge
        html = str(driver.page_source or "")

        # accept cookie presence as cleared
        if self.challenge_cookie and has_cookie(driver, self.challenge_cookie):
            return True

        # accept substring presence as cleared
        if self.challenge_substring and self.challenge_substring in html:
            return True

        # accept non challenge html
        if html and not is_challenge_page(html):
            return True

        return False

    def _wait_out_challenge(self, driver) -> bool:
        # wait out challenge page
        wait = int(self.challenge_wait)
        if wait <= 0:
            return False

        poll = float(self.challenge_poll)
        if poll <= 0.0:
            poll = 1.0

        start = time.time()
        while True:
            # check challenge cleared
            if self._challenge_cleared(driver):
                return True

            # enforce timeout
            elapsed = time.time() - start
            if elapsed >= float(wait):
                return False

            # sleep poll
            time.sleep(poll)

    def _load_backfill_cursor(self, company_code: str) -> Tuple[int, bool]:
        # load cursor from state file
        if not self.backfill_enabled:
            return (0, False)

        # read cursor state map
        state = load_bursa_backfill_state()
        return get_company_backfill_cursor(state, company_code)

    def _save_backfill_cursor(self, company_code: str, next_offset: int, done: bool):
        # save cursor into state file
        if not self.backfill_enabled:
            return

        # read state map
        state = load_bursa_backfill_state()

        # update cursor row
        state = set_company_backfill_cursor(
            state=state,
            company_code=company_code,
            next_offset=next_offset,
            done=done,
        )

        # write state file
        _ = save_bursa_backfill_state(state)

    def _compute_backfill_window(self, next_offset: int, done: bool) -> Tuple[int, int, int]:
        # compute start page and skip within page
        per_page = int(self.per_page)
        if per_page <= 0:
            per_page = 20

        # normalize offset
        off = int(next_offset)
        if off < 0:
            off = 0

        # compute page cursor
        start_page = int((off // per_page) + 1)
        skip_in_page = int(off % per_page)

        # normalize pages per run
        pages = int(self.backfill_pages_per_run)
        if pages <= 0:
            pages = int(self.api_max_pages)
        if pages <= 0:
            pages = 1

        # normalize after done pages
        after_done_pages = int(self.backfill_after_done_pages_per_run)
        if after_done_pages <= 0:
            after_done_pages = 1

        # apply done override
        if bool(done):
            pages = after_done_pages
            if bool(self.backfill_reset_offset_on_done):
                start_page = 1
                skip_in_page = 0

        return (start_page, skip_in_page, pages)

    def _fetch_detail_fileaccess_html(self, driver, detail_url: str) -> str:
        # load detail and follow iframe when needed
        _ = fetch_page_source(
            driver=driver,
            url=detail_url,
            page_load_timeout=self.page_load_timeout,
        )

        # wait for detail css
        _ = wait_for_css(
            driver=driver,
            css_selector=self.detail_wait_css,
            wait_seconds=self.wait_seconds,
            poll_seconds=self.wait_poll_seconds,
        )

        # read outer html
        outer_html = str(driver.page_source or "")
        if looks_like_bursa_fileaccess_html(outer_html):
            return outer_html

        # extract iframe url
        iframe_url = extract_fileaccess_iframe_src(outer_html, detail_url)
        if not iframe_url:
            return outer_html

        # load iframe url
        _ = fetch_page_source(
            driver=driver,
            url=iframe_url,
            page_load_timeout=self.page_load_timeout,
        )

        # wait body css
        _ = wait_for_css(
            driver=driver,
            css_selector="body",
            wait_seconds=self.wait_seconds,
            poll_seconds=self.wait_poll_seconds,
        )

        # return iframe html
        return str(driver.page_source or "")

    @component.output_types(documents=List[Document])
    def run(self, query: str) -> Dict[str, Any]:
        # run bursa selenium api extraction
        q = str(query or "").strip()
        if not q:
            # log empty query
            log_source_status(self.source_id, self.name, 0, "empty query")
            return {"documents": []}

        # resolve code from query
        code = resolve_company_code(q, self.code_map)
        if not code:
            # log missing code
            log_source_status(self.source_id, self.name, 0, "missing company code")
            return {"documents": []}

        # build listing url
        listing_url = build_company_announcement_url(code)

        # load cursor state
        next_offset, done = self._load_backfill_cursor(code)

        # compute paging window
        start_page, skip_in_page, pages_to_fetch = self._compute_backfill_window(next_offset, done)

        if self.backfill_enabled:
            # print cursor status
            print(
                f"[BURSA] backfill cursor: company={code}, "
                f"offset={next_offset}, done={done}, "
                f"start_page={start_page}, skip={skip_in_page}, pages={pages_to_fetch}"
            )

        # build chrome driver
        driver = build_chrome_driver(
            headless=self.headless,
            window_width=self.window_width,
            window_height=self.window_height,
            extra_args=self.chrome_args,
            page_load_strategy=self.page_load_strategy,
            use_profile=self.use_profile,
            user_data_dir=self.user_data_dir,
            profile_dir=self.profile_dir,
        )

        try:
            # load listing page
            listing_html = fetch_page_source(
                driver=driver,
                url=listing_url,
                page_load_timeout=self.page_load_timeout,
            )

            # handle listing challenge
            if is_challenge_page(listing_html):
                print("[BURSA] cloudflare challenge detected. complete it in opened chrome window.")
                ok = self._wait_out_challenge(driver)
                if not ok:
                    log_source_status(self.source_id, self.name, 0, "listing blocked")
                    return {"documents": []}

                # reload after challenge
                _ = fetch_page_source(
                    driver=driver,
                    url=listing_url,
                    page_load_timeout=self.page_load_timeout,
                )

            # dismiss overlays
            _ = dismiss_common_overlays(driver)

            # wait listing css
            _ = wait_for_css(
                driver=driver,
                css_selector=self.listing_wait_css,
                wait_seconds=self.wait_seconds,
                poll_seconds=self.wait_poll_seconds,
            )

            # optional scroll
            if self.scroll_enabled:
                # run scroll helper
                scroll_to_bottom(driver, steps=self.scroll_steps, sleep_seconds=self.scroll_sleep)

            # init id list
            all_ann_ids: List[str] = []
            seen = set()

            # track end of history
            end_reached = False

            # track first page skip
            first_page = True

            # collect ann ids using cursor window
            for page in range(int(start_page), int(start_page) + int(pages_to_fetch)):
                # build api url
                api_url = build_api_search_url(company_code=code, page=page)
                if not api_url:
                    continue

                # add cache bust
                api_url = f"{api_url}&_={int(time.time() * 1000)}"

                # fetch api html
                api_html = fetch_page_source(
                    driver=driver,
                    url=api_url,
                    page_load_timeout=self.page_load_timeout,
                )

                # handle api challenge
                if is_challenge_page(api_html):
                    print("[BURSA] cloudflare challenge detected on api call. complete it in opened chrome window.")
                    ok = self._wait_out_challenge(driver)
                    if not ok:
                        log_source_status(self.source_id, self.name, 0, "api blocked")
                        return {"documents": []}

                    # read current page html
                    api_html = str(driver.page_source or "")

                # extract ids from api body
                ids = self._extract_ann_ids_from_text(api_html)

                # detect end of history
                if not ids:
                    end_reached = True
                    break

                # apply skip within first page
                if first_page and skip_in_page > 0:
                    if skip_in_page >= len(ids):
                        ids = []
                    else:
                        ids = ids[skip_in_page:]
                first_page = False

                for ann_id in ids:
                    # dedupe ann ids
                    if ann_id in seen:
                        continue
                    seen.add(ann_id)
                    all_ann_ids.append(ann_id)

                    # cap by max results
                    if len(all_ann_ids) >= int(self.max_results):
                        break

                # stop on cap
                if len(all_ann_ids) >= int(self.max_results):
                    break

            if not all_ann_ids:
                # save cursor state
                if self.backfill_enabled:
                    if end_reached:
                        self._save_backfill_cursor(code, 0, True)
                    else:
                        self._save_backfill_cursor(code, next_offset, done)

                # log no urls
                log_source_status(self.source_id, self.name, 0, "no detail urls")
                return {"documents": []}

            documents: List[Document] = []

            # track processed ann ids
            processed_ann = 0

            # track dedupe urls
            seen_urls = set()

            for ann_id in all_ann_ids:
                # enforce cap
                if len(documents) >= self.max_results:
                    break

                # count processed
                processed_ann += 1

                # build detail url
                detail_url = build_detail_url_from_ann_id(ann_id)
                if not detail_url:
                    continue

                # dedupe url
                if detail_url in seen_urls:
                    continue
                seen_urls.add(detail_url)

                # fetch detail html
                detail_html = self._fetch_detail_fileaccess_html(driver, detail_url)

                # handle detail challenge
                if is_challenge_page(detail_html):
                    ok = self._wait_out_challenge(driver)
                    if not ok:
                        continue
                    detail_html = str(driver.page_source or "")

                # build structured text and meta
                detail_text, extracted_meta = build_bursa_detail_text(detail_html)

                # skip empty content
                if not str(detail_text or "").strip():
                    continue

                # read title fields
                title_text = str(extracted_meta.get("title_text") or "").strip()
                company_name = str(extracted_meta.get("company_name") or "").strip()
                source_date = extracted_meta.get("source_date")

                # build final title
                final_title = ""
                if company_name and title_text:
                    final_title = f"{company_name} - {title_text}"
                else:
                    final_title = title_text or company_name or f"bursa announcement {ann_id}"

                # build snippet
                snippet_len = int(self.config.SNIPPET_LENGTH)
                snippet = (detail_text or "")[:snippet_len].strip()

                # append detail document
                documents.append(
                    create_document(
                        source_name=self.name,
                        title=final_title,
                        url=detail_url,
                        snippet=snippet,
                        content=detail_text,
                        source_date=source_date,
                    )
                )

                # extract attachment urls
                pdf_urls = extract_attachment_urls(detail_html, self.config)
                for pdf_url in pdf_urls:
                    # enforce cap
                    if len(documents) >= self.max_results:
                        break

                    # dedupe url
                    if pdf_url in seen_urls:
                        continue
                    seen_urls.add(pdf_url)

                    # append placeholder attachment doc
                    documents.append(
                        create_document(
                            source_name=self.name,
                            title=f"{final_title} - attachment".strip(),
                            url=pdf_url,
                            snippet="",
                            content="",
                            source_date=source_date,
                        )
                    )

            # advance cursor by processed announcements
            if self.backfill_enabled:
                new_offset = int(next_offset) + int(processed_ann)
                if end_reached:
                    self._save_backfill_cursor(code, 0, True)
                else:
                    self._save_backfill_cursor(code, new_offset, False)

            # log status
            log_source_status(self.source_id, self.name, len(documents), f"company={code}")
            return {"documents": documents}
        finally:
            # close driver
            driver.quit()