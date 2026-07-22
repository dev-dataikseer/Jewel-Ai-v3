"""Tests for Admin prompt validation (placeholders + Jinja lint)."""

from app.prompt_engine.prompt_validate import validate_prompt_text


def test_validate_ok_known_placeholders():
    result = validate_prompt_text(
        "ROLE: Catalog\n{{SUBTYPE_BLOCK}}\n{{EXECUTION_BLOCK}}",
        scope="master",
        workflow="CATALOG_IMAGE",
    )
    assert result["ok"] is True
    assert result["errors"] == []
    assert "SUBTYPE_BLOCK" in result["placeholders_found"]


def test_validate_unknown_placeholder_is_error():
    result = validate_prompt_text("Hello {{NOT_A_REAL_TOKEN}}", scope="master")
    assert result["ok"] is False
    assert any("Unknown placeholder" in e for e in result["errors"])
    assert "NOT_A_REAL_TOKEN" in result["unknown_placeholders"]


def test_validate_jinja_block_is_error():
    result = validate_prompt_text("{% if true %}x{% endif %}", scope="fragment")
    assert result["ok"] is False
    assert any("Jinja" in e for e in result["errors"])


def test_validate_missing_recommended_is_warning_only():
    result = validate_prompt_text("ROLE only, no subtype token", scope="master")
    assert result["ok"] is True
    assert any("SUBTYPE_BLOCK" in w for w in result["warnings"])


def test_validate_subject_scope_allows_empty_placeholders():
    result = validate_prompt_text("Ring sits flush on the finger.", scope="subject")
    assert result["ok"] is True
    assert result["errors"] == []
