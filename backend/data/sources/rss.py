"""
rss feed retriever
fetch and filter news feeds
"""

import feedparser
from datetime import datetime
from typing import List, Dict

from haystack.core.component import component
from haystack.dataclasses import Document

from backend.configuration.sources import USER_AGENT
from backend.helpers.fetch.source_helpers import (
    extract_query_words,
    has_any_query_word,
    clean_html,
    create_document,
    log_results,
)


# ==================== RSS RETRIEVER ====================

@component
class RSSRetriever:

    def __init__(self, config, source_id: str, name: str, feed_urls: List[str]):
        # store config and ids
        self.config = config
        self.source_id = source_id
        self.name = name
        self.feed_urls = feed_urls

        # read limits
        self.max_results = int(config.SOURCE_DEFAULT_MAX_RESULTS)

    @component.output_types(documents=List[Document])
    def run(self, query: str) -> Dict[str, object]:
        # run rss retrieval
        documents = []

        # build query words
        query_words = extract_query_words(query)

        # init feed stats
        feeds_ok = 0
        feeds_fail = 0
        entries_total = 0
        entries_matched = 0

        # read rss entry cap
        max_entries = int(self.config.RSS_MAX_ENTRIES_PER_FEED)

        for feed_url in self.feed_urls:
            # parse rss feed
            feed = feedparser.parse(feed_url, agent=USER_AGENT)
            if not feed or not getattr(feed, "entries", None):
                feeds_fail += 1
                continue

            # track ok feeds
            feeds_ok += 1

            for entry in feed.entries[:max_entries]:
                # count total entries
                entries_total += 1

                # read fields
                title = clean_html(entry.get("title", ""))
                description = clean_html(entry.get("description", "") or entry.get("summary", ""))

                # skip empty rows
                if not title and not description:
                    continue

                # build match text
                text = f"{title} {description}"
                if not has_any_query_word(text, query_words, min_matches=1, full_query=query):
                    continue

                # track match stats
                entries_matched += 1

                # parse published date
                source_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    dt = datetime(*entry.published_parsed[:6])
                    source_date = dt.strftime("%Y-%m-%d")

                # read snippet cap
                snippet_len = int(self.config.SNIPPET_LENGTH)

                # build document row
                documents.append(
                    create_document(
                        source_name=self.name,
                        title=title,
                        url=entry.get("link", ""),
                        snippet=description[:snippet_len],
                        content=description,
                        source_date=source_date,
                    )
                )

                # enforce cap
                if len(documents) >= self.max_results:
                    break

            # stop on cap
            if len(documents) >= self.max_results:
                break

        # log retrieval stats
        log_results(
            self.source_id,
            documents,
            f"feeds: {feeds_ok}/{feeds_ok + feeds_fail}, entries: {entries_matched}/{entries_total}",
        )

        return {"documents": documents}