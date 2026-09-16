"""
extract text from images
download images from html
run tesseract ocr
"""

from pathlib import Path
import io
import logging
import shutil
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from PIL import Image
import pytesseract

from backend.helpers.fetch.httpx_helpers import build_httpx_client, resolve_tls_verify

# module-level logger
logger = logging.getLogger(__name__)


# ==================== TESSERACT ====================

def configure_tesseract(tesseract_cmd: str) -> bool:
    # set tesseract command path, falling back to PATH lookup
    cmd = str(tesseract_cmd or "").strip()

    if cmd:
        # validate configured path exists
        p = Path(cmd)
        if p.exists():
            pytesseract.pytesseract.tesseract_cmd = str(p)
            return True
        # configured path doesn't exist — fall through to PATH lookup
        logger.warning(f"[OCR] configured OCR_TESSERACT_CMD '{cmd}' does not exist, trying PATH")

    # fall back to PATH-based discovery
    found = shutil.which("tesseract")
    if not found:
        logger.info(
            "[OCR] tesseract binary not found (configured path invalid and not on PATH) — "
            "OCR disabled for this run"
        )
        return False

    # set command from resolved path
    pytesseract.pytesseract.tesseract_cmd = found
    return True


# ==================== URLS ====================

def extract_image_urls_from_html(html: str, page_url: str, max_images: int) -> List[str]:
    # extract image urls from html
    s = str(html or "")
    if not s.strip():
        return []

    # normalize base url
    base = str(page_url or "").strip()
    soup = BeautifulSoup(s, "html.parser")

    found = []
    seen = set()

    for img in soup.find_all("img"):
        # read src
        src = img.get("src") or ""
        src = str(src).strip()
        if not src:
            continue

        # skip inline data urls
        if src.startswith("data:"):
            continue

        # build absolute url
        full = urljoin(base, src) if base else src
        full = str(full).strip()
        if not full:
            continue

        # skip non http urls
        if not (full.startswith("http://") or full.startswith("https://")):
            continue

        # skip svg images
        if full.lower().endswith(".svg"):
            continue

        # dedupe urls
        key = full.lower()
        if key in seen:
            continue

        seen.add(key)
        found.append(full)

        # enforce cap
        if int(max_images) > 0 and len(found) >= int(max_images):
            break

    return found


# ==================== DOWNLOAD ====================

def fetch_image_bytes(client, url: str, max_bytes: int) -> bytes:
    # download image bytes
    u = str(url or "").strip()
    if not u:
        return b""

    # run request
    r = client.get(u)

    # enforce http ok
    if int(r.status_code) != 200:
        return b""

    # validate image content type
    ct = str((r.headers or {}).get("content-type", "") or "").lower()
    if not ct.startswith("image/"):
        return b""

    # read bytes
    data = bytes(r.content or b"")
    if not data:
        return b""

    # apply max bytes cap
    cap = int(max_bytes)
    if cap > 0 and len(data) > cap:
        data = data[:cap]

    return data


# ==================== OCR ====================

def ocr_image_bytes(image_bytes: bytes, lang: str, timeout: int = 10) -> str:
    # run ocr on image bytes, degrading to empty string on any failure
    if not image_bytes:
        return ""

    try:
        # open image
        img = Image.open(io.BytesIO(image_bytes))

        # run tesseract with a subprocess timeout
        text = pytesseract.image_to_string(img, lang=str(lang or ""), timeout=int(timeout))
        return str(text or "").strip()
    except pytesseract.pytesseract.TesseractNotFoundError:
        # binary vanished between configure and run
        logger.warning("[OCR] tesseract binary vanished between configure and run — skipping")
        return ""
    except RuntimeError:
        # pytesseract raises RuntimeError on subprocess timeout
        logger.warning(f"[OCR] tesseract timed out after {timeout}s — skipping image")
        return ""
    except Exception as e:
        # covers PIL decode errors (UnidentifiedImageError etc.) and anything else
        logger.warning(f"[OCR] image decode/OCR failed: {e} — skipping image")
        return ""


def ocr_from_html_images(
    html: str,
    page_url: str,
    config,
    headers: dict,
) -> str:
    # run ocr on images found in html
    if not bool(config.OCR_ENABLED):
        return ""

    # configure tesseract
    ok = configure_tesseract(config.OCR_TESSERACT_CMD)
    if not ok:
        return ""

    # read settings
    max_images = int(config.OCR_MAX_IMAGES)
    timeout = int(config.OCR_TIMEOUT)
    max_bytes = int(config.OCR_MAX_IMAGE_BYTES)
    lang = str(config.OCR_LANG)

    # build url list
    urls = extract_image_urls_from_html(html=html, page_url=page_url, max_images=max_images)
    if not urls:
        return ""

    # build client
    with build_httpx_client(
        config=config,
        timeout=timeout,
        headers=headers,
        follow_redirects=bool(config.HTTP_FOLLOW_REDIRECTS),
        verify=resolve_tls_verify(config, source_id="ocr"),
    ) as client:
        parts = []
        for u in urls:
            # fetch bytes
            data = fetch_image_bytes(
                client=client,
                url=u,
                max_bytes=max_bytes,
            )
            if not data:
                continue

            # run ocr
            text = ocr_image_bytes(image_bytes=data, lang=lang, timeout=timeout)
            if not text:
                continue

            parts.append(text)

    # join parts
    joined = "\n\n".join(parts).strip()
    return joined