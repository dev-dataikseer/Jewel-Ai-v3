"""Tests for catalog execution modes, branding clauses, and environment rotation."""

from app.pipeline.validator import normalize_jewelry_types
from app.prompt_engine.attachments import ImageContext, attachment_parts, build_catalog_attachment_mapping
from app.prompt_engine.document import PromptDocument
from app.prompt_engine.environment_rotation import (
    choose_environment,
    clear_memory_rotation_for_tests,
    get_recent_environments,
)
from app.prompt_engine.execution_mode import (
    EXECUTION_MODE_VERSION,
    ENVIRONMENT_POOL,
    append_execution_mode,
    build_branding_clause,
    build_execution_parts,
)


def test_branding_reference_no_logo_has_no_image3():
    clause = build_branding_clause(False, mode="reference")
    assert "IMAGE_3" not in clause
    assert "Image 3" not in clause
    assert "no branding" in clause.lower() or "erase" in clause.lower()


def test_branding_reference_with_logo_uses_index():
    clause = build_branding_clause(True, mode="reference", logo_image_label="Image 3")
    assert "Image 3" in clause or "logo" in clause.lower()
    assert "erase" in clause.lower() or "Apply" in clause or "apply" in clause.lower()


def test_four_flag_combos_execution_parts():
    # no ref, no logo
    parts, mode, meta = build_execution_parts(has_reference=False, has_logo=False, environment=ENVIRONMENT_POOL[0])
    assert mode == "modern_dynamic_catalog"
    assert "CHOSEN_ENVIRONMENT" not in parts[0].text  # substituted
    assert ENVIRONMENT_POOL[0][:20] in parts[0].text or "environment" in parts[0].text.lower()
    assert "Image 3" not in parts[0].text
    assert "no branding" in parts[0].text.lower() or "branding" in parts[0].text.lower()

    # no ref + logo
    parts, mode, _ = build_execution_parts(
        has_reference=False, has_logo=True, environment=ENVIRONMENT_POOL[1], logo_index=2
    )
    assert mode == "modern_dynamic_catalog"
    assert "logo" in parts[0].text.lower() or "Image 2" in parts[0].text
    assert "Image 3" not in parts[0].text

    # ref, no logo
    parts, mode, _ = build_execution_parts(
        has_reference=True, has_logo=False, catalog_mode="reference_mirror"
    )
    assert mode == "reference_mirroring"
    assert "REFERENCE" in parts[0].text.upper() or "Image 2" in parts[0].text
    assert "Image 3" not in parts[0].text
    assert "no branding" in parts[0].text.lower() or "erase" in parts[0].text.lower()

    # ref + logo
    parts, mode, _ = build_execution_parts(
        has_reference=True, has_logo=True, logo_index=3, catalog_mode="reference_mirror"
    )
    assert mode == "reference_mirroring"
    assert "Image 3" in parts[0].text or "logo" in parts[0].text.lower()


def test_append_execution_mode_debug():
    doc = PromptDocument()
    out, mode, meta = append_execution_mode(
        doc, has_reference=False, has_logo=False, environment=ENVIRONMENT_POOL[2]
    )
    assert mode == "modern_dynamic_catalog"
    assert out.debug["execution_mode_version"] == EXECUTION_MODE_VERSION
    assert any(p.key == "exec_modern_catalog" for p in out.parts)


def test_catalog_attachment_map_no_dangling_logo():
    part = build_catalog_attachment_mapping(
        ImageContext(
            has_product=True,
            has_style_reference=True,
            has_logo=False,
            roles=[{"index": 1, "role": "product"}, {"index": 2, "role": "theme"}],
        )
    )
    assert "Image 1" in part.text
    assert "ENVIRONMENT REFERENCE" in part.text or "REFERENCE" in part.text.upper()
    assert "LOGO" not in part.text.upper() or "logo" not in part.text.split("Image 1")[0].lower()
    assert "COMPANY LOGO" not in part.text
    assert "- Image 3" not in part.text

    part = build_catalog_attachment_mapping(
        ImageContext(
            has_product=True,
            has_style_reference=False,
            has_logo=True,
            roles=[{"index": 1, "role": "product"}, {"index": 2, "role": "logo"}],
        )
    )
    assert "Image 2" in part.text and "LOGO" in part.text.upper()
    assert "ENVIRONMENT REFERENCE" not in part.text

    part = build_catalog_attachment_mapping(
        ImageContext(
            has_product=True,
            has_style_reference=True,
            has_logo=True,
            roles=[
                {"index": 1, "role": "product"},
                {"index": 2, "role": "theme"},
                {"index": 3, "role": "logo"},
            ],
        )
    )
    assert "Image 3" in part.text and "LOGO" in part.text.upper()


def test_catalog_attachment_parts_use_role_map():
    parts = attachment_parts(
        "CATALOG_IMAGE",
        ImageContext(has_product=True, has_style_reference=True, has_logo=False),
    )
    keys = {p.key for p in parts}
    assert "attach_role_map" in keys
    assert "attach_catalog_theme" not in keys


def test_environment_rotation_avoids_recent():
    clear_memory_rotation_for_tests()
    uid = "test-user-rotate"
    first = choose_environment(uid, "job-1")
    assert first in ENVIRONMENT_POOL
    recent = get_recent_environments(uid, lookback=5)
    assert first in recent
    seen = {first}
    for i in range(min(8, len(ENVIRONMENT_POOL) - 1)):
        pick = choose_environment(uid, f"job-{i + 2}")
        if len(ENVIRONMENT_POOL) > 5:
            assert pick in ENVIRONMENT_POOL
        seen.add(pick)
    assert len(seen) >= 2


def test_subtype_order_deterministic():
    assert normalize_jewelry_types(["Necklace", "Ring"]) == ["Ring", "Necklace"]
    assert normalize_jewelry_types(["Bracelet", "Ring", "Necklace"]) == [
        "Ring",
        "Necklace",
        "Bracelet",
    ]
