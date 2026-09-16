"""
initialize app components on startup
load database and ai models
validate system configuration
"""

from backend.configuration.config import config as config_dict
from backend.helpers.logic.helper import ensure_directories
from backend.data.database import ProfilesDatabase
from backend.data.document_store import get_document_store
from backend.pipeline import Pipeline


# ==================== COMPONENT INITIALIZATION ====================

def init_components(app):
    # ensure storage directories
    ensure_directories()

    # print initialization header
    print("=" * 20 + " COMPONENTS INITIALIZATION " + "=" * 20 + "\n")

    # get environment from app config, trust it, no silent default fallback
    env = app.config["ENV"]
    config_class = config_dict[env]

    # create components storage dict
    components = {
        "profiles_db": None,
        "doc_store": None,
        "pipeline": None,
        "config": config_class,
    }

    # initialize document store
    print("─" * 70 + "\n[1/3] Document Store (ChromaDB)\n" + "─" * 70)
    components["doc_store"] = get_document_store(config_class)
    print("[OK]\n")

    # initialize profiles database
    print("─" * 70 + "\n[2/3] Profiles Database (SQLite)\n" + "─" * 70)
    components["profiles_db"] = ProfilesDatabase(config=config_class)
    print("[OK]\n")

    # initialize pipeline
    print("─" * 70 + "\n[3/3] Pipeline\n" + "─" * 70)
    components["pipeline"] = Pipeline(
        config=config_class,
        document_store=components["doc_store"],
    )
    print("[OK]\n")

    # print completion message
    print("=" * 20 + " INITIALIZATION COMPLETE " + "=" * 20 + "\n")

    # return initialized components
    return components