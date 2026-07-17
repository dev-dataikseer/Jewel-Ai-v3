"""Tests for model-aware prompt engine packing."""

from app.prompt_engine.attachments import ImageContext, append_attachments, attachment_parts
from app.prompt_engine.document import PromptDocument, PromptPart
from app.prompt_engine.model_adapter import adapt_document, pack_parts
from app.prompt_engine.profiles import resolve_prompt_profile
from app.providers.model_catalog.spec import ImageContract, ModelSpec, ModelUiMeta
from app.providers.prompt_augment import augment_prompt_for_workflow


def _fake_spec(*, family: str = "nano_banana", max_chars: int | None = 3600, omit: bool = False) -> ModelSpec:
    return ModelSpec(
        endpoint_id=f"test/{family}",
        display_name=family,
        family=family,
        category="edit",
        capabilities={},
        input_schema={},
        default_params={},
        image=ImageContract(mode="urls_array", max_prompt_chars=max_chars, omit_prompt=omit),
        ui=ModelUiMeta(provider="fal", provider_label="fal", tasks=("i2i",)),
    )


def test_pack_parts_drops_optional_first():
    parts = [
        PromptPart("crit", "C" * 100, "critical", "master"),
        PromptPart("opt", "O" * 100, "optional", "attachment"),
        PromptPart("imp", "I" * 100, "important", "master"),
    ]
    kept, dropped = pack_parts(parts, max_chars=220)
    assert "opt" in dropped
    assert any(p.key == "crit" for p in kept)
    assert _join(kept) <= 220 or len(_join(kept)) <= 220


def _join(parts: list[PromptPart]) -> int:
    return len(" ".join(p.text for p in parts))


def test_adapt_respects_nano_budget():
    long = "word " * 900
    doc = PromptDocument(
        parts=[
            PromptPart("preservation_lock", "Preserve geometry exactly.", "critical", "master"),
            PromptPart("prose", long, "important", "master"),
            PromptPart("scrub", "Exclude watermarks.", "optional", "attachment"),
        ]
    )
    final = adapt_document(doc, model_spec=_fake_spec(family="nano_banana", max_chars=3600))
    assert final.char_count <= 3600
    assert final.max_chars == 3600
    assert "Preserve geometry" in final.text


def test_omit_prompt_for_vton_style_models():
    doc = PromptDocument(parts=[PromptPart("a", "hello", "critical", "master")])
    final = adapt_document(doc, model_spec=_fake_spec(family="vton", max_chars=800, omit=True))
    assert final.text == ""
    assert final.debug["adapter"] == "omit_prompt"


def test_attachments_dedupe_scrub_when_master_covers_it():
    doc = PromptDocument(
        parts=[
            PromptPart(
                "preservation_lock",
                "Exclude watermarks and overlay text artifacts from source photos.",
                "critical",
                "master",
            )
        ]
    )
    out = append_attachments(doc, "CATALOG_IMAGE", ImageContext(has_product=True))
    assert not any(p.key == "artifact_scrub" for p in out.parts)


def test_catalog_theme_attachment_when_reference():
    parts = attachment_parts("CATALOG_IMAGE", ImageContext(has_product=True, has_style_reference=True))
    keys = {p.key for p in parts}
    assert "attach_catalog_theme" in keys


def test_legacy_augment_wrapper():
    out = augment_prompt_for_workflow(
        "REFERENCE_STYLE_MATCH",
        "Base catalog prompt.",
        has_style_reference=True,
    )
    assert "Base catalog prompt" in out
    assert "ATTACHED IMAGES" in out


def test_resolve_profile_by_family():
    profile = resolve_prompt_profile(_fake_spec(family="flux_kontext", max_chars=None))
    assert profile.name == "flux_kontext"
    assert profile.prefer_short_subject is True
    assert profile.max_chars == 2800
    assert profile.official_status in ("documented", "undocumented", "estimated_effective")


def test_gpt_official_capacity_clamps_recommended():
    from app.prompt_engine.capacity import packing_budget, OfficialPromptCapacity

    # Official documented limit always wins when tighter
    assert packing_budget(
        recommended_max_chars=50_000,
        official=OfficialPromptCapacity(32_000, "documented"),
    ) == 32_000
    # Undocumented official does not clamp recommended
    assert packing_budget(
        recommended_max_chars=3600,
        official=OfficialPromptCapacity(None, "undocumented"),
    ) == 3600


def test_gpt_profile_uses_recommended_under_official():
    image = ImageContract(
        mode="urls_array",
        max_prompt_chars=12_000,
        recommended_max_prompt_chars=12_000,
        official_max_prompt_chars=32_000,
        official_prompt_status="documented",
    )
    spec = ModelSpec(
        endpoint_id="openai/gpt-image-2/edit",
        display_name="GPT",
        family="gpt_image",
        category="edit",
        capabilities={},
        input_schema={},
        default_params={},
        image=image,
        ui=ModelUiMeta(provider="openai", provider_label="OpenAI", tasks=("i2i",)),
    )
    profile = resolve_prompt_profile(spec)
    assert profile.max_chars == 12_000
    assert profile.official_max_chars == 32_000
    assert profile.official_status == "documented"
