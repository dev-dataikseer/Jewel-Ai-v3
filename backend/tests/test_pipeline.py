import pytest
from app.pipeline.composer import ComposeInput, slugify
from app.pipeline.validator import validate_job_create, whitelist_job_fields


def test_slugify():
    assert slugify("Ruby Red") == "ruby_red"
    assert slugify("White Gold / Platinum") == "white_gold_platinum"


def test_variant_field_mapping():
    from app.pipeline.composer import VARIANT_FIELD_MAP

    assert VARIANT_FIELD_MAP["GEMSTONE_COLOR_CHANGE"] == "gemstone_target_color"
    assert VARIANT_FIELD_MAP["LUXURY_ENHANCEMENT"] == "metal_type"


def test_whitelist_job_fields():
    body = {"workflow": "CATALOG_IMAGE", "asset_id": "x", "hack": "evil"}
    assert "hack" not in whitelist_job_fields(body)


def test_rate_tools_rejected():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        validate_job_create({"workflow": "RATE_TOOLS"})
    assert exc.value.status_code == 400
