"""
centralize all file paths
define directory structure
provide path utilities
"""

from pathlib import Path


# ==================== BASE PATHS ====================

PROJECT_ROOT = Path(__file__).resolve().parents[2]        # project root
BACKEND_DIR = PROJECT_ROOT / "backend"                    # backend dir
FRONTEND_DIR = PROJECT_ROOT / "frontend"                  # frontend dir
CONFIG_DIR = BACKEND_DIR / "configuration"                # config dir


# ==================== DATA PATHS ====================

DATA_DIR = BACKEND_DIR / "data"                           # data dir
STORES_DIR = DATA_DIR / "stores"                          # stores dir

SQLITE_DB_PATH = STORES_DIR / "sqlite3.db"                # sqlite db path
CHROMA_DB_PATH = STORES_DIR / "chroma_db"                 # chroma dir path
SELENIUM_PROFILE_PATH = STORES_DIR / "selenium_profile"   # selenium profile dir

BURSA_BACKFILL_STATE_PATH = STORES_DIR / "bursa_backfill.json"  # bursa cursor path

SEED_URLS_PATH = STORES_DIR / "seed_urls.json"            # seed urls path
SEED_ENTITIES_PATH = STORES_DIR / "seed_entities.json"    # seed entities path
SEED_ENTITY_CANDIDATES_PATH = STORES_DIR / "seed_entity_candidates.json"  # seed candidates path


# ==================== CONFIGURATION FILES ====================

CUSTOM_PERSPECTIVES_PATH = CONFIG_DIR / "custom_perspectives.json"  # perspectives path
CUSTOM_MODELS_PATH = CONFIG_DIR / "custom_models.json"              # models path
COMMONCRAWL_INDICES_PATH = CONFIG_DIR / "commoncrawl_indices.json"  # indices path
BURSA_COMPANY_CODES_PATH = CONFIG_DIR / "bursa_company_codes.json"  # bursa codes path


# ==================== FRONTEND PATHS ====================

FLASK_INSTANCE_DIR = FRONTEND_DIR / "flaskr" / "instance"  # flask instance dir
STATIC_DIR = FRONTEND_DIR / "flaskr" / "static"            # static dir
TEMPLATES_DIR = FRONTEND_DIR / "flaskr" / "templates"      # templates dir