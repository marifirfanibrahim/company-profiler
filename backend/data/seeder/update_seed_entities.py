"""
update seed entities
use llm generator
write entity list
"""

import sys


# ==================== IMPORTS ====================

from backend.configuration.config import get_config
from backend.configuration.paths import SEED_ENTITIES_PATH
from backend.configuration.seeding import SEED_QUERY_MAX_TOKENS, SEED_ENV
from backend.configuration.prompts import SEED_QUERY_GENERATOR_TEMPLATE
from backend.models.generator import get_generator
from backend.helpers.persist.json_utils import safe_extract_queries, save_json, load_json


# ==================== MAIN LOGIC ====================

def build_seed_entities(env: str):
    # load config class
    config_cls = get_config(env)

    # build config instance
    config = config_cls()

    # load existing entities from json
    existing = load_json(SEED_ENTITIES_PATH, default=[])
    if not isinstance(existing, list):
        existing = []

    existing_cleaned = []
    existing_seen = set()

    for item in existing:
        # validate item type
        if not isinstance(item, str):
            continue

        # normalize string
        s = item.strip()
        if not s:
            continue

        # dedupe values
        key = s.lower()
        if key in existing_seen:
            continue

        # store seen key
        existing_seen.add(key)
        existing_cleaned.append(s)

    # init llm generator
    llm = get_generator(config, model_id=config.DEFAULT_OLLAMA_MODEL)

    # warm up generator
    if hasattr(llm, "warm_up"):
        llm.warm_up()

    # build prompt with existing entities inline
    existing_str = ", ".join(existing_cleaned) if existing_cleaned else ""
    prompt = SEED_QUERY_GENERATOR_TEMPLATE.format(existing_entities=existing_str)

    # run llm
    result = llm.run(prompt=prompt, max_tokens=int(SEED_QUERY_MAX_TOKENS))

    # read reply text
    if isinstance(result, dict):
        replies = result.get("replies") or []
        raw = replies[0] if replies else ""
    else:
        raw = str(result)

    # extract raw items from llm text
    raw_items = safe_extract_queries(raw)

    new_cleaned = []
    new_seen = set(existing_seen)

    for item in raw_items:
        # validate item type
        if not isinstance(item, str):
            continue

        # normalize string
        s = item.strip()
        if not s:
            continue

        # normalize lower value
        low = s.lower()

        # skip preface lines
        if low.startswith("here is") or low.startswith("here are"):
            continue
        if "queries" in low or "json" in low:
            continue

        # strip leading backslashes
        while s and s[0] == "\\":
            s = s[1:]

        # strip trailing backslashes
        while s and s[-1] == "\\":
            s = s[:-1]

        # normalize trimmed string
        s = s.strip()

        # strip leading quote
        if s.startswith('"'):
            s = s[1:].strip()

        # strip trailing quote
        if s.endswith('"'):
            s = s[:-1].strip()

        # strip trailing comma
        s = s.rstrip(",").strip()

        # skip empty content
        if not s:
            continue

        # skip json fragments
        if any(ch in s for ch in "{}[]"):
            continue

        # dedupe new values
        key = s.lower()
        if key in new_seen:
            continue

        # store new values
        new_seen.add(key)
        new_cleaned.append(s)

    # merge existing and new
    merged = existing_cleaned + new_cleaned

    # save merged list to json
    save_json(SEED_ENTITIES_PATH, merged)

    # print save summary
    print(f"[SEED_ENTITIES] existing={len(existing_cleaned)}, added={len(new_cleaned)}, total={len(merged)}")


if __name__ == "__main__":
    # read env argument
    if len(sys.argv) > 1:
        # read argv value
        env_arg = sys.argv[1].strip()

        # normalize env value
        env_val = env_arg or SEED_ENV
    else:
        # set default env
        env_val = SEED_ENV

    # run update command
    build_seed_entities(env=env_val)