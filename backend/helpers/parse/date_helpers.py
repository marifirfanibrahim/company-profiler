"""
parse date strings
extract date tokens
return ymd values
"""

import re
from datetime import datetime, timezone
from typing import List, Optional


# ==================== PATTERNS ====================

DATE_PATTERNS = [
    r"(\d{4}-\d{2}-\d{2})",
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})",
    r"(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})",
    r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
]


# ==================== FORMAT ====================

def is_leap_year(year: int) -> bool:
    # check leap year
    y = int(year)

    # apply century rule
    if (y % 400) == 0:
        return True
    if (y % 100) == 0:
        return False

    # apply quad rule
    return (y % 4) == 0


def days_in_month(year: int, month: int) -> int:
    # return days in month
    m = int(month)

    # map month lengths
    if m in [1, 3, 5, 7, 8, 10, 12]:
        return 31
    if m in [4, 6, 9, 11]:
        return 30
    if m == 2:
        return 29 if is_leap_year(int(year)) else 28

    # reject invalid month
    return 0


def format_ymd(year: int, month: int, day: int) -> str:
    # format yyyy-mm-dd
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _valid_ymd(year: int, month: int, day: int) -> bool:
    # validate ymd ranges
    y = int(year)
    m = int(month)
    d = int(day)

    # validate year range
    if y < 1900 or y > 2100:
        return False

    # validate month range
    if m < 1 or m > 12:
        return False

    # validate day range
    dim = days_in_month(y, m)
    if dim <= 0:
        return False
    if d < 1 or d > dim:
        return False

    return True


# ==================== PARSE ====================

def parse_yyyy_mm_dd(value: str) -> Optional[str]:
    # parse yyyy-mm-dd only
    s = str(value or "").strip()
    if not s:
        return None

    # read fixed segment
    s = s[:10]

    # match yyyy-mm-dd
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if not m:
        return None

    # parse parts
    year = int(m.group(1))
    month = int(m.group(2))
    day = int(m.group(3))

    # validate parts
    if not _valid_ymd(year, month, day):
        return None

    return format_ymd(year, month, day)


def parse_dd_mm_yyyy(value: str) -> Optional[str]:
    # parse dd/mm/yyyy and variants
    s = str(value or "").strip()
    if not s:
        return None

    # match dmy variants
    m = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$", s)
    if not m:
        return None

    # parse parts
    day = int(m.group(1))
    month = int(m.group(2))
    year = int(m.group(3))

    # validate parts
    if not _valid_ymd(year, month, day):
        return None

    return format_ymd(year, month, day)


def parse_yyyy_mm_dd_slash(value: str) -> Optional[str]:
    # parse yyyy/mm/dd and variants
    s = str(value or "").strip()
    if not s:
        return None

    # match ymd slash variants
    m = re.match(r"^(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})$", s)
    if not m:
        return None

    # parse parts
    year = int(m.group(1))
    month = int(m.group(2))
    day = int(m.group(3))

    # validate parts
    if not _valid_ymd(year, month, day):
        return None

    return format_ymd(year, month, day)


def parse_month_name_date(value: str) -> Optional[str]:
    # parse month name date forms
    s = str(value or "").strip()
    if not s:
        return None

    # normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # map month tokens
    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    # match dd mon yyyy
    m1 = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})$", s)
    if m1:
        # parse parts
        day = int(m1.group(1))
        mon = str(m1.group(2) or "")[:3].lower()
        year = int(m1.group(3))

        # validate month token
        if mon not in month_map:
            return None

        # map month value
        month = int(month_map[mon])

        # validate parts
        if not _valid_ymd(year, month, day):
            return None

        return format_ymd(year, month, day)

    # match mon dd yyyy
    m2 = re.match(r"^([A-Za-z]{3,})\s+(\d{1,2}),?\s+(\d{4})$", s)
    if m2:
        # parse parts
        mon = str(m2.group(1) or "")[:3].lower()
        day = int(m2.group(2))
        year = int(m2.group(3))

        # validate month token
        if mon not in month_map:
            return None

        # map month value
        month = int(month_map[mon])

        # validate parts
        if not _valid_ymd(year, month, day):
            return None

        return format_ymd(year, month, day)

    return None


def parse_date_to_yyyy_mm_dd(value: str) -> Optional[str]:
    # parse multiple date formats
    s = str(value or "").strip()
    if not s:
        return None

    # normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # try ymd dash
    out = parse_yyyy_mm_dd(s)
    if out:
        return out

    # try dmy variants
    out = parse_dd_mm_yyyy(s)
    if out:
        return out

    # try ymd slash variants
    out = parse_yyyy_mm_dd_slash(s)
    if out:
        return out

    # try month name date
    out = parse_month_name_date(s)
    if out:
        return out

    return None


# ==================== EXTRACT ====================

def extract_first_date_token(text: str, patterns: Optional[List[str]] = None) -> str:
    # extract first matched date token
    s = str(text or "")
    if not s.strip():
        return ""

    # select pattern list
    pats = list(patterns) if patterns is not None else list(DATE_PATTERNS)

    for pat in pats:
        # search first match
        m = re.search(pat, s, flags=re.IGNORECASE)
        if not m:
            continue

        # return matched group
        token = str(m.group(1) or "").strip()
        if token:
            return token

    return ""


# ==================== DATETIME ====================

def parse_yyyy_mm_dd_datetime(value: str) -> Optional[datetime]:
    # parse yyyy-mm-dd to utc datetime
    ymd = parse_yyyy_mm_dd(value)
    if not ymd:
        return None

    # parse parts
    year = int(ymd[0:4])
    month = int(ymd[5:7])
    day = int(ymd[8:10])

    # return utc datetime
    return datetime(year, month, day, tzinfo=timezone.utc)