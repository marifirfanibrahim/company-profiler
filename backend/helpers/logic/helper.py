"""
shared helpers
centralize common functions
wrap configuration access
set hf hub env
"""

import os

from backend.configuration.prompts import SYSTEM_PROMPT
from backend.configuration.paths import STORES_DIR, CHROMA_DB_PATH, FLASK_INSTANCE_DIR


def get_system_prompt() -> str:
    # return global system prompt
    return SYSTEM_PROMPT


def ensure_directories():
    # create all required directories
    directories = [
        STORES_DIR,
        CHROMA_DB_PATH,
        FLASK_INSTANCE_DIR,
    ]

    for directory in directories:
        # create directory
        directory.mkdir(parents=True, exist_ok=True)


def apply_hf_hub_env(config):
    # set hf hub env values
    max_retries = int(config.HF_HUB_MAX_RETRIES)
    timeout = int(config.HF_HUB_HTTP_TIMEOUT)

    # set retry env var
    os.environ["HF_HUB_MAX_RETRIES"] = str(max_retries)

    # set timeout env var
    os.environ["HF_HUB_HTTP_TIMEOUT"] = str(timeout)


__all__ = [
    "get_system_prompt",
    "ensure_directories",
    "apply_hf_hub_env",
]