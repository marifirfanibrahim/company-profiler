"""
source factory for creating retrievers
"""

from typing import Dict, Any

from backend.configuration.sources import RSS_SOURCES
from .rss import RSSRetriever
from .commoncrawl import CommonCrawlRetriever
from .official_cases import OfficialCasesRetriever
from .bursa import BursaRetriever
from .ram_ratings import RAMRatingsRetriever
from .marc_ratings import MARCRatingsRetriever


# ==================== FACTORY FUNCTION ====================

def get_all_retrievers(config) -> Dict[str, Any]:
    # build dict of all retrievers
    retrievers: Dict[str, Any] = {}

    # read disabled sources
    disabled = config.DISABLED_SOURCES

    # attach official sources retriever
    if "official_sources" not in disabled:
        retrievers["official_sources"] = OfficialCasesRetriever(config)

    # attach bursa retriever
    if "bursa" not in disabled:
        retrievers["bursa"] = BursaRetriever(config)

    # attach ram retriever
    if "ram_ratings" not in disabled:
        retrievers["ram_ratings"] = RAMRatingsRetriever(config)

    # attach marc retriever
    if "marc_ratings" not in disabled:
        retrievers["marc_ratings"] = MARCRatingsRetriever(config)

    # attach commoncrawl retriever
    if "commoncrawl" not in disabled:
        retrievers["commoncrawl"] = CommonCrawlRetriever(config)

    # attach rss retrievers
    for source_id, source_config in RSS_SOURCES.items():
        # skip disabled rss source
        if source_id in disabled:
            continue

        # build rss retriever
        retrievers[source_id] = RSSRetriever(
            config=config,
            source_id=source_id,
            name=source_config["name"],
            feed_urls=source_config["feeds"],
        )

    return retrievers