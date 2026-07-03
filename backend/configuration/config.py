"""
configuration system for application
manage environment settings
define model parameters and thresholds
centralize all settings
no defaults - fail fast on missing config
"""

from backend.configuration.labels import ENTITY_LABELS, RELATIONSHIP_LABELS, QUERY_ENTITY_LABELS


# ==================== BASE CONFIGURATION ====================

class Config:


    # ------------------ ENVIRONMENT ------------------

    DEBUG = False                                         # default false
    TESTING = False                                       # default false


    # ------------------ APPLICATION ------------------

    APP_VERSION = "0.5.7"                                 # default 0.5.7


    # ------------------ CORS ------------------

    CORS_ORIGINS = ["http://localhost:5000"]              # default local origin


    # ------------------ TIME ------------------

    DATE_STAMP_FORMAT = "%Y-%m-%d"                        # default %Y-%m-%d


    # ------------------ API ------------------

    PROFILES_API_DEFAULT_LIMIT = 30                       # default 30
    PROFILES_STORE_DOCUMENTS = True                       # default true
    PROFILES_STORE_DOCUMENTS_MAX_DOCS = 25                # default 25
    PROFILES_STORE_DOCUMENTS_MAX_CONTENT_CHARS = 2000     # default 2000


    # ------------------ MODELS ------------------

    # default llm models
    DEFAULT_OLLAMA_MODEL = "llama3:8b"                    # default llama3:8b
    DEFAULT_OPENAI_MODEL = "gpt-4o-mini"                  # default gpt-4o-mini
    DEFAULT_ANTHROPIC_MODEL = "claude-3-sonnet-20240229"  # default claude-3-sonnet-20240229

    # classifiers
    GLINER_MODEL = "urchade/gliner_multi"                 # default urchade/gliner_multi
    GLIREL_MODEL = "jackboyla/glirel-large-v0"            # default jackboyla/glirel-large-v0
    RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"            # default BAAI/bge-reranker-v2-m3

    # nli
    FACT_CHECK_MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"  # default mdeberta xnli

    # embedder
    EMBEDDER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # default all-MiniLM-L6-v2


    # ------------------ API KEYS ------------------

    OPENAI_API_KEY = "sk-proj-xxx"                        # default placeholder
    ANTHROPIC_API_KEY = "sk-ant-api03-xxx"                # default placeholder
    ANTHROPIC_API_VERSION = "2023-06-01"                  # default 2023-06-01


    # ------------------ FEATURES ------------------

    ENABLE_DB_INDEXING = True                             # default true
    DISABLED_SOURCES = []                                 # default empty
    ENABLE_FACT_CHECKING = True                           # default true
    ENABLE_ENTITY_EXTRACTION = True                       # default true
    ENABLE_RELATIONSHIPS = True                           # default true


    # ------------------ HF HUB ------------------

    HF_HUB_MAX_RETRIES = 0                                # default 0
    HF_HUB_HTTP_TIMEOUT = 60                              # default 60


    # ------------------ OUTPUT ------------------

    OUTPUT_META_DROP_KEYS = [                             # default list
        "source_id",
        "split_id",
        "split_idx_start",
        "_split_overlap",
    ]


    # ------------------ SEARCH SETTINGS ------------------

    SOURCE_DEFAULT_TIMEOUT = 10                           # default 10
    SOURCE_DEFAULT_MAX_RESULTS = 10                       # default 10


    # ------------------ CONTENT EXTRACTION ------------------

    CONTENT_EXTRACT_TIMEOUT = 15                          # default 15
    CONTENT_EXTRACT_MAX_DOCS = 10                         # default 10
    CONTENT_EXTRACT_WORKERS = 1                           # default 1
    MIN_CONTENT_LENGTH = 100                              # default 100

    # pdf specific threshold
    PDF_MIN_CONTENT_LENGTH = 50                           # default 50

    CONTENT_EXISTING_THRESHOLD = 1000                     # default 1000, skip fetch when content long
    CONTENT_MAX_EXTRACT_CHARS = 20000                     # default 20000, cap stored text
    CONTENT_DATE_SEARCH_CHARS = 2000                      # default 2000, cap date scan text
    SNIPPET_LENGTH = 300                                  # default 300

    CONTENT_PDF_URL_KEYWORDS = [                          # default list
        "disclosure.bursamalaysia.com/fileaccess/apbursaweb/download",
        "/fileaccess/apbursaweb/download",
        "ea_ds_attachments",
    ]

    CONTENT_SKIP_DOMAINS = [                              # default list
        "twitter.com",
        "x.com",
        "facebook.com",
        "instagram.com",
        "youtube.com",
        "reddit.com",
        "linkedin.com",
        "tiktok.com",
    ]


    # ------------------ OCR ------------------

    OCR_ENABLED = False                                   # default false
    OCR_TESSERACT_CMD = "C:\\path\\to\\tesseract.exe"     # default placeholder
    OCR_LANG = "eng-ms"                                   # default eng-ms
    OCR_TIMEOUT = 10                                      # default 10
    OCR_MAX_IMAGES = 3                                    # default 3
    OCR_MAX_IMAGE_BYTES = 2000000                         # default 2000000
    OCR_MIN_TEXT_LENGTH = 80                              # default 80, merge gate


    # ------------------ PDF EXTRACTION ------------------

    PDF_EXTRACT_ENABLED = True                            # default true
    PDF_EXTRACT_MAX_PAGES = 30                            # default 30
    PDF_EXTRACT_MAX_CHARS = 20000                         # default 20000
    PDF_EXTRACT_JOIN = "\n\n"                             # default \n\n


    # ------------------ RERANKER ------------------

    RERANKER_MAX_LENGTH = 512                             # default 512
    MIN_RELEVANCE_SCORE = 50.0                            # default 50.0, score gate
    DIVERSITY_PENALTY = 0.9                               # default 0.9, domain penalty
    TOP_K_DIVERSE = 5                                     # default 5
    TOP_K_RESULTS = 10                                    # default 10
    RERANKER_MIN_DOC_LENGTH = 50                          # default 50
    RERANKER_MAX_DOC_CHARS = 2000                         # default 2000


    # ------------------ LLM GENERATION ------------------

    OLLAMA_HOST = "http://localhost:11434"                # default localhost
    LLM_TIMEOUT = 1200                                    # default 1200
    LLM_TEMPERATURE = 0.7                                 # default 0.7
    LLM_TOP_P = 0.9                                       # default 0.9
    LLM_NUM_PREDICT = 300                                 # default 300, token budget


    # ------------------ ENTITY EXTRACTION ------------------

    GLINER_THRESHOLD = 0.5                                # default 0.5, score gate
    GLINER_LABELS = ENTITY_LABELS                         # default ENTITY_LABELS


    # ------------------ RELATIONSHIP EXTRACTION ------------------

    GLIREL_THRESHOLD = 0.4                                # default 0.4, score gate
    GLIREL_MAX_TOKENS = 512                               # default 512
    GLIREL_TOP_K = 10                                     # default 10
    GLIREL_LABELS = RELATIONSHIP_LABELS                   # default RELATIONSHIP_LABELS


    # ------------------ QUERY ENTITY LABELS ------------------

    QUERY_ENTITY_LABELS = QUERY_ENTITY_LABELS             # default QUERY_ENTITY_LABELS


    # ------------------ FACT CHECKER ------------------

    FACT_CHECK_THRESHOLD = 0.25                           # default 0.25, score fallback
    FACT_CHECK_MIN_SOURCE_LENGTH = 50                     # default 50, evidence gate
    FACT_CHECK_PREMISE_MAX_CHARS = 1500                   # default 1500, cap premise text

    FACT_CHECK_MAX_CLAIMS = 10                            # default 10, claim cap
    FACT_CHECK_MIN_CLAIM_LENGTH = 20                      # default 20, claim gate
    FACT_CHECK_TOP_K_EVIDENCE = 3                         # default 3, evidence cap

    FACT_CHECK_NEUTRAL_WEIGHT = 0.5                       # default 0.5, support weight
    FACT_CHECK_CONTRADICTION_THRESHOLD = 0.9              # default 0.9, drop gate
    FACT_CHECK_ENTAILMENT_MAX_FOR_CONTRADICTION = 0.05    # default 0.05, drop gate


    # ------------------ DOCUMENT PROCESSING ------------------

    DOCUMENT_SPLIT_LENGTH = 100                           # default 100
    DOCUMENT_SPLIT_OVERLAP = 20                           # default 20
    SUMMARIZATION_MAX_DOCS = 15                           # default 15, prompt chunk cap


    # ------------------ SNAPSHOT AND PROFILE ------------------

    SNAPSHOT_MAX_DOC_CHARS = 1500                         # default 1500, prompt doc cap
    SNAPSHOT_MAX_TOKENS = 100                             # default 100, token budget

    PROFILE_MAX_DOC_CHARS = 1500                          # default 1500, prompt doc cap
    PROFILE_MAX_TOKENS = 400                              # default 400, token budget
    PROFILE_ENTITY_MAX_TEXT_CHARS = 8000                  # default 8000, ner text cap
    PROFILE_MAX_ENTITIES_FOR_CONTEXT = 30                 # default 30, context cap
    PROFILE_MAX_RELATIONSHIPS_FOR_CONTEXT = 40            # default 40, context cap


    # ------------------ DATABASE ------------------

    DATABASE_RETRIEVAL_LIMIT = 25                         # default 25
    DATABASE_MIN_CONTENT_LENGTH = 50                      # default 50
    DATABASE_MAX_INDEX_DOCS = 40                          # default 40, index cap
    DATABASE_INDEX_TRUNCATE_LENGTH = 0                    # default 0
    DATABASE_MIN_SIMILARITY = 0.0                         # default 0.0


    # ------------------ CHROMADB ------------------

    CHROMA_COLLECTION_NAME = "company_profiler_store"               # default company_profiler_store


    # ------------------ ANALYTICS ------------------

    TOP_ENTITY_MIN_CONFIDENCE = 0.8                       # default 0.8, report gate
    TOP_RELATIONSHIP_MIN_CONFIDENCE = 0.8                 # default 0.8, report gate


    # ------------------ COMMON CRAWL ------------------

    COMMONCRAWL_TIMEOUT = 30                              # default 30
    COMMONCRAWL_MAX_RESULTS = 30                          # default 30
    COMMONCRAWL_MAX_INDEX_HITS = 50                       # default 50, index cap
    COMMONCRAWL_FETCH_WORKERS = 5                         # default 5
    COMMONCRAWL_MAX_INDICES = 99                          # default 99
    COMMONCRAWL_HITS_PER_INDEX = 50                       # default 50

    COMMONCRAWL_DOMAIN_SCAN_LIMIT = 10                    # default 10, domain scan cap
    COMMONCRAWL_PATTERN_LIMIT = 2                         # default 2, pattern cap

    COMMONCRAWL_FORCE_CONNECTION_CLOSE = True             # default true, set connection close


    # ------------------ PIPELINE ------------------

    RETRIEVER_MAX_WORKERS = 4                             # default 4
    RETRIEVER_TASK_TIMEOUT = 10                           # default 10
    RETRIEVER_GLOBAL_TIMEOUT = 30                         # default 30

    MAX_SNIPPETS = 1                                      # default 1
    DEDUPE_CONTENT_JACCARD = 0.85                         # default 0.85, overlap gate
    DEDUPE_MIN_WORD_LENGTH = 3                            # default 3
    DEDUPE_MAX_CHARS = 2000                               # default 2000

    # db query expansion
    PIPELINE_ENABLE_QUERY_EXPANSION = True                # default true
    PIPELINE_QUERY_EXPANSION_MAX_QUERIES = 6              # default 6, query cap

    # reranker selection
    PIPELINE_ENABLE_RERANKING = True                      # default true
    PIPELINE_RERANK_TOP_DOCS = 10                         # default 10, doc cap
    PIPELINE_RERANK_CHUNKS = True                         # default true
    PIPELINE_RERANK_CHUNK_CANDIDATES = 80                 # default 80, chunk cap

    # newer preference
    PIPELINE_PREFER_NEWER = True                          # default true
    PIPELINE_RECENCY_WEIGHT = 0.15                        # default 0.15, score weight
    PIPELINE_RECENCY_HALF_LIFE_DAYS = 30                  # default 30, decay days

    # cache confidence weight
    PIPELINE_CACHE_CONFIDENCE_WEIGHT = 0.20               # default 0.20, score weight

    # network fetch
    PIPELINE_CONTENT_FETCH_ENABLED = False                # default false

    # phrase filter
    PIPELINE_PHRASE_FILTER_ENABLED = True                 # default true
    PIPELINE_PHRASE_FILTER_MIN_CHARS = 6                  # default 6, gate chars

    # high risk filter
    PIPELINE_HIGH_RISK_FILTER_ENABLED = True              # default true
    PIPELINE_HIGH_RISK_SELF_MIN_CHARS = 6                 # default 6, gate chars


    # ------------------ CONFIDENCE ------------------

    CONFIDENCE_USE_FACT_CHECK = True                      # default true
    CONFIDENCE_FACT_CHECK_MIN_MULT = 0.6                  # default 0.6, mult min
    CONFIDENCE_FACT_CHECK_MAX_MULT = 1.0                  # default 1.0, mult max


    # ------------------ RSS / COMMONCRAWL ------------------

    RSS_MAX_ENTRIES_PER_FEED = 30                         # default 30
    COMMONCRAWL_QUERY_LIMIT = 20                          # default 20
    COMMONCRAWL_FETCH_TIMEOUT = 60                        # default 60
    COMMONCRAWL_MIN_CONTENT_LENGTH = 100                  # default 100
    COMMONCRAWL_MAX_CONTENT_CHARS = 15000                 # default 15000
    TITLE_TRUNCATE_LENGTH = 100                           # default 100


    # ------------------ HTTP CLIENT POOL ------------------

    HTTP_MAX_KEEPALIVE_CONNECTIONS = 20                   # default 20
    HTTP_MAX_CONNECTIONS = 100                            # default 100

    HTTP_VERIFY_TLS = False                               # default false
    HTTP_FOLLOW_REDIRECTS = True                          # default true
    HTTP_FORCE_CONNECTION_CLOSE = False                   # default false


# ==================== ENVIRONMENT CONFIGS ====================

class DevelopmentConfig(Config):
    DEBUG = True                                          # default true
    ENV = "development"                                   # default development


class ProductionConfig(Config):
    DEBUG = False                                         # default false
    ENV = "production"                                    # default production


class TestingConfig(Config):
    TESTING = True                                        # default true
    ENV = "testing"                                       # default testing


# ==================== CONFIG LOADER MAP ====================

config = {
    "development": DevelopmentConfig,                     # default map
    "production": ProductionConfig,                       # default map
    "testing": TestingConfig,                             # default map
    "default": DevelopmentConfig,                         # default map
}


def get_config(env: str = "development"):
    # return config class for environment
    return config.get(env, config["default"])