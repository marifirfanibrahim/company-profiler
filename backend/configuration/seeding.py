"""
centralized seeding configuration options
seeding behavior and scheduler settings
"""

# llm seed generation
SEED_QUERY_MAX_TOKENS = 120                              # default 120

# scheduler / env
SEED_SCHEDULER_ENABLED = True                            # default true
SEED_INTERVAL_MINUTES = 20                               # default 20
SEED_ENTITY_UPDATE_INTERVAL_MINUTES = 15                 # default 15
SEED_ENTITY_UPDATE_ENABLED = False                       # default false
SEED_START_IMMEDIATELY = True                            # default true
SEED_ENV = "development"                                 # default development

# seeding extraction
SEED_CONTENT_EXTRACT_MAX_DOCS = 80                       # default 80

# seeding concurrency
SEED_CONCURRENT_ITEMS_ENABLED = True                    # default false
SEED_CONCURRENT_ITEMS_PER_BATCH = 3                      # default 3
SEED_CONCURRENT_ITEMS_WORKERS = 3                        # default 3

# seeding reranker
SEED_RERANK_SKIP_SOURCES = [                             # default list
    "RAM Ratings",
    "MARC Ratings",
]

# cache sources
SEED_BASE_SOURCE_CACHE_SOURCES = [                       # default base cache sources
    "official_sources",
    "bursa",
    "commoncrawl",
    "ram_ratings",
    "marc_ratings",
]

# retrievers
SEED_ACTIVE_RETRIEVERS = [
    "official_sources",
    "bursa",
    "ram_ratings",
    "marc_ratings",
    "commoncrawl",
    "news_feeds",
    "google_news",
]                                                        # default active retrievers

# settings
SEED_ROUND_DELAY = 15                                    # default 15
SEED_MAX_ROUNDS = 60                                     # default 60


# ==================== CACHE ====================

SEED_BASE_SOURCE_CACHE_ENABLED = False                   # default false
SEED_BASE_SOURCE_CACHE_TTL_SECONDS = 0                   # default 0


# ==================== EXPANSION ====================

SEED_EXPANSION_ENABLED = True                            # default true
SEED_EXPANSION_PROMOTION_ENABLED = True                  # default true
SEED_EXPANSION_PROMOTION_INTERVAL_MINUTES = 10           # default 10

SEED_EXPANSION_MAX_CANDIDATES_PER_PROFILE = 12           # default 12
SEED_EXPANSION_MAX_CUSTOMER_GUARANTOR_PER_PROFILE = 6    # default 6
SEED_EXPANSION_MAX_HIGH_RISK_PER_PROFILE = 8             # default 8

SEED_EXPANSION_MIN_MENTIONS = 1                          # default 1
SEED_EXPANSION_MIN_CONTEXT_HITS = 1                      # default 1

SEED_EXPANSION_CONTEXT_WINDOW_CHARS = 140                # default 140
SEED_EXPANSION_PROMOTE_MIN_SCORE = 0.50                  # default 0.50
SEED_EXPANSION_MAX_PROMOTIONS_PER_RUN = 20               # default 20

SEED_EXPANSION_CUSTOMER_KEYWORDS = [                     # default customer keywords
    "customer",
    "borrower",
    "issuer",
    "obligor",
    "facility",
    "financing",
    "loan",
    "term loan",
    "sukuk",
    "programme",
    "information memorandum",
]

SEED_EXPANSION_GUARANTOR_KEYWORDS = [                    # default guarantor keywords
    "guarantor",
    "guarantee",
    "corporate guarantee",
    "penjamin",
    "jaminan",
    "jaminan korporat",
]

SEED_EXPANSION_HIGH_RISK_KEYWORDS = [                    # default high risk keywords
    "investigation",
    "charged",
    "lawsuit",
    "court",
    "fraud",
    "corruption",
    "money laundering",
    "enforcement action",
    "regulatory action",
    "disciplinary",
    "sanction",
    "penalty",
    "fine",
    "convicted",
    "arrested",
    "macc",
    "sprm",
    "pdrm",
    "bnm enforcement",
    "sc malaysia",
    "bursa enforcement",
]


# ==================== DYNAMIC ====================

SEED_DYNAMIC_RELOAD_ENABLED = True                       # default true
SEED_DYNAMIC_RELOAD_EVERY_ROUNDS = 3                     # default 3
SEED_DYNAMIC_PROMOTE_EVERY_ROUNDS = 1                    # default 1

SEED_DYNAMIC_PRIORITY_ENABLED = True                     # default true
SEED_DYNAMIC_PRIORITY_MAX_ENTITIES = 50                  # default 50
SEED_DYNAMIC_PRIORITY_MAX_QUERIES_PER_ENTITY = 8         # default 8
SEED_DYNAMIC_PRIORITY_PREFER_BASE_QUERY = True           # default true