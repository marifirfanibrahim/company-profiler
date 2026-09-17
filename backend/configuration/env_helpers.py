"""
typed environment variable readers
wrap os.environ access with coercion and fail-fast semantics
no defaults - fail fast on missing required values
"""

import logging
import os

# module-level logger
logger = logging.getLogger(__name__)

# recognized boolean tokens, compared after strip + lowercase
_TRUE_VALUES = ("1", "true", "yes", "on")
_FALSE_VALUES = ("0", "false", "no", "off")


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

    # treat unset or blank/whitespace-only as the given default, matching env_str
    if val is None or val.strip() == "":
        return default

    # normalize for case-insensitive comparison
    low = val.strip().lower()

    # coerce recognized truthy tokens
    if low in _TRUE_VALUES:
        return True

    # coerce recognized falsy tokens
    if low in _FALSE_VALUES:
        return False

    # warn on an unrecognized value and keep the default rather than guessing
    logger.warning(
        f"environment variable '{name}' has unrecognized boolean value '{val}'; "
        f"expected one of {_TRUE_VALUES + _FALSE_VALUES} - using default {default}"
    )
    return default


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
