"""Post-process shop logo under generated jewelry images."""

from __future__ import annotations

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)


def composite_logo_beneath(
    image_bytes: bytes,
    logo_bytes: bytes,
    *,
    bar_ratio: float = 0.12,
    logo_max_height_ratio: float = 0.70,
    padding_ratio: float = 0.08,
    bar_color: tuple[int, int, int] = (255, 255, 255),
) -> bytes:
    """
    Place the shop logo centered on a bar beneath the product image.

    Returns PNG bytes. Falls back to original image bytes on failure.
    """
    try:
        product = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    except Exception:
        return image_bytes

    width, height = product.size
    bar_h = max(48, int(height * bar_ratio))
    canvas = Image.new("RGBA", (width, height + bar_h), (*bar_color, 255))
    canvas.paste(product, (0, 0))

    max_logo_h = int(bar_h * logo_max_height_ratio)
    max_logo_w = int(width * (1 - 2 * padding_ratio))
    lw, lh = logo.size
    scale = min(max_logo_w / max(lw, 1), max_logo_h / max(lh, 1), 1.0)
    new_w = max(1, int(lw * scale))
    new_h = max(1, int(lh * scale))
    logo_resized = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)

    x = (width - new_w) // 2
    y = height + (bar_h - new_h) // 2
    canvas.paste(logo_resized, (x, y), logo_resized)

    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


def load_logo_bytes_from_storage(logo_url: str, storage) -> bytes | None:
    """Read logo bytes from local/object storage, or SSRF-safe fetch for absolute URLs."""
    if not logo_url:
        return None
    path = logo_url.split("?", 1)[0]
    if path.startswith("http://") or path.startswith("https://"):
        try:
            from app.security.url_fetch import safe_fetch_image_bytes_sync

            return safe_fetch_image_bytes_sync(path, timeout=30.0)
        except Exception as exc:
            logger.debug("Logo remote fetch failed for %s: %s", path[:80], exc)
            return None
    if path.startswith("/uploads/"):
        key = path.removeprefix("/uploads/").lstrip("/")
    elif path.startswith("uploads/"):
        key = path.removeprefix("uploads/").lstrip("/")
    else:
        return None
    try:
        data, _ctype = storage.read_upload(key)
        return data
    except Exception:
        return None
