"""Tests for Prompt Profile V2 compose (JSON key→value, two pages)."""

from app.prompt_engine.attachments import ImageContext
from app.prompt_engine.profile_compose import (
    REF_WITH,
    REF_WITHOUT,
    filter_conditional_keys,
    has_secondary_images,
    parse_header_text,
    resolve_reference_mode,
    serialize_sections,
)


def test_parse_header_text_basic():
    raw = "ROLE: Photographer.\n\nCAMERA: 100mm macro.\nLIGHTING: Soft box."
    sections = parse_header_text(raw)
    assert sections["ROLE"] == "Photographer."
    assert sections["CAMERA"] == "100mm macro."
    assert "Soft box" in sections["LIGHTING"]


def test_serialize_sections_splits_negative():
    text, negatives = serialize_sections(
        {
            "ROLE": "Photographer",
            "NEGATIVE PROMPT": "CGI, watermark",
            "CAMERA": "100mm",
        }
    )
    assert "ROLE: Photographer" in text
    assert "CAMERA: 100mm" in text
    assert "NEGATIVE" not in text
    assert negatives == ["CGI, watermark"]


def test_reference_mode_from_images():
    product_only = ImageContext(has_product=True)
    assert resolve_reference_mode(product_only) == REF_WITHOUT
    assert not has_secondary_images(product_only)

    # Logo alone is branding — must not select with_reference page.
    with_logo = ImageContext(has_product=True, has_logo=True)
    assert resolve_reference_mode(with_logo) == REF_WITHOUT
    assert not has_secondary_images(with_logo)

    with_theme = ImageContext(has_product=True, has_style_reference=True)
    assert resolve_reference_mode(with_theme) == REF_WITH
    assert has_secondary_images(with_theme)

    with_portrait = ImageContext(has_product=True, has_portrait=True)
    assert resolve_reference_mode(with_portrait) == REF_WITH


def test_filter_conditional_keys_drops_logo_without_logo_image():
    sections = {
        "ROLE": "Photographer",
        "LOGO_USE": "Apply the logo watermark",
        "REFERENCE_USE": "Mirror Image 2",
    }
    ctx = ImageContext(has_product=True, has_style_reference=False, has_logo=False)
    filtered = filter_conditional_keys(sections, ctx)
    assert "ROLE" in filtered
    assert "LOGO_USE" not in filtered
    assert "REFERENCE_USE" not in filtered

    ctx2 = ImageContext(has_product=True, has_style_reference=True, has_logo=True)
    filtered2 = filter_conditional_keys(sections, ctx2)
    assert "LOGO_USE" in filtered2
    assert "REFERENCE_USE" in filtered2
