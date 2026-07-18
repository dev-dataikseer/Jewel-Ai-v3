"""Tests for UI-managed fragments, workflow resolve, and catalog modes."""

from __future__ import annotations

from app.prompt_engine.attachments import ImageContext, attachment_parts
from app.prompt_engine.custom_guard import sanitize_custom_change
from app.prompt_engine.execution_mode import (
    EXECUTION_MODE_VERSION,
    append_execution_mode,
    bookend_fidelity_lock,
    build_branding_clause,
    build_execution_parts,
)
from app.prompt_engine.document import PromptDocument, PromptPart
from app.prompt_engine.environment_rotation import choose_environment, clear_memory_rotation_for_tests
from app.prompt_engine.fragment_defaults import (
    DEFAULT_FRAGMENTS,
    FIDELITY_LOCK,
    substitute,
)
from app.prompt_engine.workflow_resolve import resolve_workflow


def test_resolve_legacy_try_on():
    r = resolve_workflow("JEWELRY_ON_MODEL")
    assert r.workflow == "VIRTUAL_TRY_ON"
    assert r.try_on_mode == "studio"
    r2 = resolve_workflow("CUSTOMER_TRY_ON")
    assert r2.try_on_mode == "customer"
    r3 = resolve_workflow("VIRTUAL_TRY_ON", try_on_mode="customer")
    assert r3.workflow == "VIRTUAL_TRY_ON"
    assert r3.try_on_mode == "customer"


def test_resolve_style_match_to_catalog():
    r = resolve_workflow("REFERENCE_STYLE_MATCH")
    assert r.workflow == "CATALOG_IMAGE"
    assert r.catalog_mode == "style_mood"
    r2 = resolve_workflow("BULK_GENERATION")
    assert r2.workflow == "CATALOG_IMAGE"


def test_substitute_clears_unknown():
    assert "{{X}}" not in substitute("Hello {{NAME}} {{X}}", {"NAME": "World"})
    assert "World" in substitute("Hello {{NAME}}", {"NAME": "World"})


def test_fidelity_lock_bookend():
    doc = PromptDocument(parts=[PromptPart(key="body", text="BODY", priority="critical", source="master")])
    out, meta = bookend_fidelity_lock(doc, db=None)
    texts = [p.text for p in out.parts]
    assert texts[0] == DEFAULT_FRAGMENTS[FIDELITY_LOCK]
    assert texts[-1] == DEFAULT_FRAGMENTS[FIDELITY_LOCK]
    assert "BODY" in texts


def test_execution_modes_four_branding_combos():
    for has_ref, has_logo in [(False, False), (False, True), (True, False), (True, True)]:
        parts, mode, meta = build_execution_parts(
            has_reference=has_ref,
            has_logo=has_logo,
            environment="Test surface.",
            logo_index=3 if has_logo else None,
            catalog_mode="reference_mirror" if has_ref else "modern",
            db=None,
        )
        text = parts[0].text
        assert "IMAGE_3" not in text or has_logo
        if has_logo:
            assert "Image 3" in text or "BRAND" in text
        else:
            assert "Image 3" not in text
            assert "no branding" in text.lower() or "cleanup" in text.lower() or "do not add" in text.lower()
        assert mode in ("reference_mirroring", "modern_dynamic_catalog")


def test_style_mood_execution():
    parts, mode, _ = build_execution_parts(
        has_reference=True,
        has_logo=False,
        catalog_mode="style_mood",
        db=None,
    )
    assert mode == "style_mood"
    assert "STYLE EXTRACTION" in parts[0].text or "lighting" in parts[0].text.lower()


def test_catalog_attachments_no_dangling_logo():
    ctx = ImageContext(has_product=True, has_style_reference=True, has_logo=False, image_count=2)
    parts = attachment_parts("CATALOG_IMAGE", ctx, db=None)
    joined = "\n".join(p.text for p in parts)
    assert "COMPANY LOGO" not in joined
    assert "Image 1" in joined or "PRIMARY SUBJECT" in joined


def test_try_on_attachment_virtual():
    ctx = ImageContext(has_product=True, has_portrait=True, image_count=2)
    parts = attachment_parts("VIRTUAL_TRY_ON", ctx, db=None)
    assert any(p.key == "attach_try_on" for p in parts)


def test_branding_clause_from_fragments():
    clause = build_branding_clause(False, mode="catalog", db=None)
    assert "no branding" in clause.lower() or "Do not add" in clause


def test_env_rotation_uses_pool():
    clear_memory_rotation_for_tests()
    a = choose_environment("test-user-frag", "j1", pool=["Env A", "Env B"])
    b = choose_environment("test-user-frag", "j2", pool=["Env A", "Env B"])
    assert a in ("Env A", "Env B")
    assert b in ("Env A", "Env B")


def test_custom_guard_softens_alter():
    cleaned, hits = sanitize_custom_change("Please resize the ring and keep gold")
    assert hits
    assert "do not apply jewelry-altering" in (cleaned or "").lower()


def test_append_execution_mode_version():
    doc = PromptDocument(parts=[PromptPart(key="m", text="x", priority="critical", source="master")])
    out, mode, meta = append_execution_mode(
        doc, has_reference=False, has_logo=False, environment="Stone.", catalog_mode="modern"
    )
    assert mode == "modern_dynamic_catalog"
    assert out.debug.get("execution_mode_version") == EXECUTION_MODE_VERSION
    assert "Stone." in out.parts[-1].text
