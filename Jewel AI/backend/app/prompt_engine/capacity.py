"""
Official provider prompt capacity vs internal PromptProfile budgets.

Official values come from provider docs when published.
recommended_* values are Jewel AI engineering heuristics for packing quality/latency —
they are NOT the same as API hard limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.providers.model_catalog.spec import ModelSpec

OfficialStatus = Literal["documented", "undocumented", "estimated_effective"]


@dataclass(frozen=True)
class OfficialPromptCapacity:
    """Provider-documented (or explicitly undocumented) prompt capacity."""

    max_chars: int | None
    status: OfficialStatus
    note: str | None = None


# --- Official capacities (from provider documentation where available) ---

OFFICIAL_GPT_IMAGE = OfficialPromptCapacity(
    32_000, "documented", "OpenAI GPT Image 2: 32,000 characters"
)
OFFICIAL_IMAGEN = OfficialPromptCapacity(480, "documented", "Google Imagen 4: 480 characters")
OFFICIAL_IDEOGRAM = OfficialPromptCapacity(1_000, "documented", "Ideogram 3: 1,000 characters")
OFFICIAL_RECRAFT = OfficialPromptCapacity(10_000, "documented", "Recraft V3: 10,000 characters")
OFFICIAL_GEMINI_IMAGE = OfficialPromptCapacity(
    None,
    "undocumented",
    "Gemini / Nano Banana image models: no published character limit (large token context)",
)
OFFICIAL_FLUX = OfficialPromptCapacity(
    None,
    "estimated_effective",
    "BFL FLUX family: no hard published limit; ~256–512 effective tokens commonly cited",
)
OFFICIAL_SDXL = OfficialPromptCapacity(
    None,
    "estimated_effective",
    "Stable Diffusion XL: ~77 effective CLIP tokens (~300 characters practical)",
)
OFFICIAL_UNKNOWN = OfficialPromptCapacity(
    None, "undocumented", "No published prompt character limit from provider"
)

_OFFICIAL_BY_FAMILY: dict[str, OfficialPromptCapacity] = {
    "gpt_image": OFFICIAL_GPT_IMAGE,
    "nano_banana": OFFICIAL_GEMINI_IMAGE,
    "flux_kontext": OFFICIAL_FLUX,
    "flux2_edit": OFFICIAL_FLUX,
    "flux_i2i": OFFICIAL_FLUX,
    "t2i": OFFICIAL_FLUX,
    "seedream": OFFICIAL_UNKNOWN,
    "grok": OFFICIAL_UNKNOWN,
    "vton": OFFICIAL_UNKNOWN,
    "ideogram": OFFICIAL_IDEOGRAM,
    "recraft": OFFICIAL_RECRAFT,
    "imagen": OFFICIAL_IMAGEN,
    "sdxl": OFFICIAL_SDXL,
    "generic": OFFICIAL_UNKNOWN,
}


def resolve_official_capacity(model_spec: "ModelSpec | None") -> OfficialPromptCapacity:
    if not model_spec:
        return OFFICIAL_UNKNOWN
    # Explicit override on ImageContract wins
    if model_spec.image.official_max_prompt_chars is not None or model_spec.image.official_prompt_status != "undocumented":
        return OfficialPromptCapacity(
            model_spec.image.official_max_prompt_chars,
            model_spec.image.official_prompt_status,  # type: ignore[arg-type]
            model_spec.image.official_prompt_note,
        )
    eid = (model_spec.endpoint_id or "").lower()
    if "ideogram" in eid:
        return OFFICIAL_IDEOGRAM
    if "recraft" in eid:
        return OFFICIAL_RECRAFT
    if "imagen" in eid:
        return OFFICIAL_IMAGEN
    if "stable-diffusion-xl" in eid or "sdxl" in eid:
        return OFFICIAL_SDXL
    family = model_spec.family or "generic"
    return _OFFICIAL_BY_FAMILY.get(family, OFFICIAL_UNKNOWN)


def packing_budget(
    *,
    recommended_max_chars: int | None,
    official: OfficialPromptCapacity,
) -> int | None:
    """
    Effective char budget for prompt packing.

    Prefer the engineering recommended budget.
    When an official documented limit exists and is tighter, never exceed it.
    """
    rec = recommended_max_chars
    if official.status == "documented" and official.max_chars is not None:
        if rec is None:
            return official.max_chars
        return min(rec, official.max_chars)
    return rec
