"""
extract pdf text
join page strings
limit output size
"""

import io
from typing import List


# ============== PDF PARSE ==============

def extract_pdf_text_from_bytes(pdf_bytes: bytes, max_pages: int, max_chars: int, joiner: str) -> str:
    # validate bytes
    if not pdf_bytes:
        return ""

    # import reader lazily
    from pypdf import PdfReader

    # open bytes buffer
    buf = io.BytesIO(pdf_bytes)

    # build reader
    reader = PdfReader(buf)

    # clamp pages
    page_count = len(reader.pages)
    cap = int(max_pages)
    if cap <= 0:
        cap = page_count
    if cap > page_count:
        cap = page_count

    parts: List[str] = []
    for i in range(cap):
        # read page
        page = reader.pages[i]

        # extract page text
        text = page.extract_text() or ""
        text = str(text).strip()

        # append page text
        if text:
            parts.append(text)

        # enforce char cap
        joined = (joiner or "\n\n").join(parts)
        if int(max_chars) > 0 and len(joined) >= int(max_chars):
            joined = joined[: int(max_chars)]
            return joined.strip()

    # join all parts
    out = (joiner or "\n\n").join(parts).strip()

    # enforce final cap
    if int(max_chars) > 0 and len(out) > int(max_chars):
        out = out[: int(max_chars)].strip()

    return out