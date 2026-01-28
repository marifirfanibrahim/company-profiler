"""
json helpers
safe json io
llm text parsing
"""

import json
import re
from pathlib import Path
import threading
import os


# ============== FILE LOCK ==============

_path_locks = {}
_path_locks_guard = threading.Lock()


def _get_path_lock(path: Path):
    # get lock for path
    p = Path(path).resolve()
    key = str(p)

    with _path_locks_guard:
        # get or create lock
        lock = _path_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _path_locks[key] = lock

    return lock


# ============== JSON IO ==============

def load_json(path, default=None):
    # normalize path object
    p = Path(path)

    # lock file access
    lock = _get_path_lock(p)
    with lock:
        # check file exists
        if not p.exists():
            return default

        # skip empty files
        size = int(p.stat().st_size)
        if size <= 0:
            return default

        # read file text
        text = p.read_text(encoding="utf-8")

        # skip whitespace only
        if not str(text).strip():
            return default

        # parse json
        data = json.loads(text)
        return data


def save_json(path, data):
    # normalize path object
    p = Path(path)

    # lock file access
    lock = _get_path_lock(p)
    with lock:
        # ensure parent directory
        p.parent.mkdir(parents=True, exist_ok=True)

        # build json text
        text = json.dumps(data, ensure_ascii=False, indent=2)

        # write file in place
        with p.open("w", encoding="utf-8", newline="\n") as f:
            # write json text
            f.write(text)

            # flush buffers
            f.flush()

            # sync file state
            os.fsync(f.fileno())

        # return status flag
        return True


# ============== JSON TEXT ==============

def extract_first_json_object(text: str) -> str:
    # extract first json object substring
    s = str(text or "")
    if not s.strip():
        return ""

    # find first brace
    start = s.find("{")
    if start < 0:
        return ""

    # track parse state
    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(s)):
        # read current char
        ch = s[i]

        if escape:
            # skip escaped char
            escape = False
            continue

        if ch == "\\":
            # set escape within string
            if in_string:
                escape = True
            continue

        if ch == '"':
            # toggle string state
            in_string = not in_string
            continue

        if in_string:
            # skip structure in string
            continue

        if ch == "{":
            # increase depth
            depth += 1
            continue

        if ch == "}":
            # decrease depth
            depth -= 1
            if depth == 0:
                out = s[start:i + 1].strip()
                return out
            if depth < 0:
                return ""

    return ""


# ============== LLM QUERIES ==============

def safe_extract_queries(text: str):
    # handle empty input
    if not text:
        return []

    # search json queries block
    pattern = r'"queries"\s*:\s*\[(.*?)\]'
    match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)

    if match:
        # extract list content
        inner = match.group(1)

        # extract quoted strings
        items = re.findall(r'"([^"]+)"', inner)

        # clean and filter items
        cleaned = []
        for item in items:
            s = str(item).strip()
            if not s:
                continue
            cleaned.append(s)
        if cleaned:
            return cleaned

    # fallback to line based parse
    lines = re.split(r'[\r\n]+', str(text))
    queries = []

    for line in lines:
        # normalize line
        s = line.strip()
        if not s:
            continue

        # remove leading bullets
        s = re.sub(r'^[-•*]\s*', "", s)
        s = s.strip()
        if not s:
            continue

        # skip structural lines
        lower = s.lower()
        if "queries" in lower and ":" in s:
            continue
        if s.startswith("{") or s.startswith("}") or s.startswith("[") or s.startswith("]"):
            continue

        # append query item
        queries.append(s)

    return queries