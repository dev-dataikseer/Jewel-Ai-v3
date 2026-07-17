"""Per-family prompt packing profiles (engineering heuristics, not API hard limits).

See ``capacity.py`` for official provider capacities.
``PromptProfile.max_chars`` is the recommended packing budget used by ModelAdapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.prompt_engine.capacity import packing_budget, resolve_official_capacity

if TYPE_CHECKING:
    from app.providers.model_catalog.spec import ModelSpec


@dataclass(frozen=True)
class PromptProfile:
    name: str
    max_chars: int | None
    omit_prompt: bool = False
    prefer_short_subject: bool = False
    # Informative — copied from OfficialPromptCapacity for debug/UI
    official_max_chars: int | None = None
    official_status: str = "undocumented"
    official_note: str | None = None


# Recommended packing budgets (heuristics for quality / latency / truncation safety).
DEFAULT_PROFILE = PromptProfile(name="default", max_chars=4000)
NANO_PROFILE = PromptProfile(name="nano_banana", max_chars=3600)  # practical safe budget; official undocumented
GPT_PROFILE = PromptProfile(name="gpt_image", max_chars=12_000)  # official 32k — keep headroom for attachments
KONTEXT_PROFILE = PromptProfile(name="flux_kontext", max_chars=2800, prefer_short_subject=True)
FLUX2_PROFILE = PromptProfile(name="flux2_edit", max_chars=3200, prefer_short_subject=True)
SEEDREAM_PROFILE = PromptProfile(name="seedream", max_chars=3500)
GROK_PROFILE = PromptProfile(name="grok", max_chars=3000)
VTON_PROFILE = PromptProfile(name="vton", max_chars=800, prefer_short_subject=True)
T2I_PROFILE = PromptProfile(name="t2i", max_chars=2500)
IDEOGRAM_PROFILE = PromptProfile(name="ideogram", max_chars=1000)  # matches official
RECRAFT_PROFILE = PromptProfile(name="recraft", max_chars=8000)  # under official 10k
IMAGEN_PROFILE = PromptProfile(name="imagen", max_chars=480)  # matches official
SDXL_PROFILE = PromptProfile(name="sdxl", max_chars=300, prefer_short_subject=True)


_FAMILY_PROFILES: dict[str, PromptProfile] = {
    "nano_banana": NANO_PROFILE,
    "gpt_image": GPT_PROFILE,
    "flux_kontext": KONTEXT_PROFILE,
    "flux2_edit": FLUX2_PROFILE,
    "flux_i2i": FLUX2_PROFILE,
    "seedream": SEEDREAM_PROFILE,
    "grok": GROK_PROFILE,
    "vton": VTON_PROFILE,
    "t2i": T2I_PROFILE,
    "ideogram": IDEOGRAM_PROFILE,
    "recraft": RECRAFT_PROFILE,
    "imagen": IMAGEN_PROFILE,
    "sdxl": SDXL_PROFILE,
    "generic": DEFAULT_PROFILE,
}


def resolve_prompt_profile(model_spec: "ModelSpec | None") -> PromptProfile:
    if not model_spec:
        return DEFAULT_PROFILE
    if model_spec.image.omit_prompt:
        return PromptProfile(name="omit", max_chars=0, omit_prompt=True)

    family = model_spec.family or model_spec.builder_id or "generic"
    eid = (model_spec.endpoint_id or "").lower()
    if "ideogram" in eid:
        family = "ideogram"
    elif "recraft" in eid:
        family = "recraft"
    elif "imagen" in eid:
        family = "imagen"
    elif "stable-diffusion-xl" in eid or "/sdxl" in eid:
        family = "sdxl"

    base = _FAMILY_PROFILES.get(family, DEFAULT_PROFILE)
    official = resolve_official_capacity(model_spec)

    # Seed/config recommended override (legacy key: max_prompt_chars)
    recommended = (
        model_spec.image.recommended_max_prompt_chars
        if model_spec.image.recommended_max_prompt_chars is not None
        else model_spec.image.max_prompt_chars
    )
    if recommended is None:
        recommended = base.max_chars

    effective = packing_budget(recommended_max_chars=recommended, official=official)

    return PromptProfile(
        name=base.name,
        max_chars=effective,
        omit_prompt=base.omit_prompt,
        prefer_short_subject=base.prefer_short_subject,
        official_max_chars=official.max_chars,
        official_status=official.status,
        official_note=official.note,
    )
