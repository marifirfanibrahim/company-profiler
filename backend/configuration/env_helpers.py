"""
typed environment variable readers
wrap os.environ access with coercion and fail-fast semantics
no defaults - fail fast on missing required values
"""

import os


def env_str(name: str, default: str = None, required: bool = False) -> str:
    # read raw string value from environment
    val = os.environ.get(name)

    # treat a blank/whitespace-only value as unset
    if val is None or val.strip() == "":
        if required:
            raise RuntimeError(
                f"required environment variable '{name}' is not set. "
                f"Set it in your .env file or process environment."
            )
        return default

    # strip surrounding whitespace before returning
    return val.strip()


def env_bool(name: str, default: bool = False) -> bool:
    # read raw value from environment
    val = os.environ.get(name)

    # unset falls back to the given default
    if val is None:
        return default

    # coerce common truthy strings, case-insensitively
    return val.strip().lower() in ("1", "true", "yes", "on")


def env_int(name: str, default: int = None, required: bool = False) -> int:
    # reuse env_str for the raw read plus required/blank handling
    val = env_str(name, default=None, required=required)

    # unset with required=False returns the given default
    if val is None:
        return default

    # coerce to int, failing fast on a non-numeric value
    try:
        return int(val)
    except ValueError:
        raise RuntimeError(f"environment variable '{name}' must be an integer, got '{val}'")
