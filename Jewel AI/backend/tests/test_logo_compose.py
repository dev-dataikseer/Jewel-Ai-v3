"""Tests for shop logo post-compose under generated images."""

from io import BytesIO

from PIL import Image

from app.storage.logo_compose import composite_logo_beneath


def _png_bytes(size: tuple[int, int], color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", size, color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_composite_logo_beneath_extends_canvas():
    product = _png_bytes((200, 200), (240, 240, 240))
    logo = _png_bytes((80, 40), (20, 20, 20))
    out = composite_logo_beneath(product, logo)
    result = Image.open(BytesIO(out))
    assert result.size[0] == 200
    assert result.size[1] > 200


def test_composite_logo_beneath_invalid_logo_returns_original():
    product = _png_bytes((100, 100), (255, 255, 255))
    out = composite_logo_beneath(product, b"not-an-image")
    assert out == product
