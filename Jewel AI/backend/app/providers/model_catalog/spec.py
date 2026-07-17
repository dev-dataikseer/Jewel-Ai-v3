"""Typed model catalog contracts for fal.ai image models."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Literal

ImageMode = Literal["urls_array", "single_url", "try_on_fields", "try_on_ordered", "none"]
TaskKind = Literal["i2i", "t2i", "vton", "edit"]


SYSTEM_FIELDS: frozenset[str] = frozenset(
    {
        "prompt",
        "instruction",
        "image_url",
        "image_urls",
        "negative_prompt",
        "mask_url",
        "mask_image_url",
        "model_image",
        "garment_image",
        "person_image_url",
        "clothing_image_url",
        "human_image_url",
        "garment_image_url",
        "reference_image_url",
    }
)


@dataclass(frozen=True)
class ImageContract:
    """How a model expects input images on the fal request body."""

    mode: ImageMode
    image_field: str = "image_urls"
    min_images: int = 1
    max_images: int = 14
    roles: tuple[str, ...] = ("product", "reference")
    try_on_fields: dict[str, str] = dc_field(default_factory=dict)
    try_on_image_order: tuple[str, ...] = ()
    product_image_index: int = 0
    person_image_index: int = 1
    reference_image_field: str | None = None
    omit_prompt: bool = False
    prompt_field: str = "prompt"
    # Legacy alias for recommended packing budget (BC with seeds / builders).
    max_prompt_chars: int | None = None
    # Explicit recommended packing budget (PromptProfile heuristic).
    recommended_max_prompt_chars: int | None = None
    # Official provider capacity (may be None when undocumented).
    official_max_prompt_chars: int | None = None
    official_prompt_status: str = "undocumented"
    official_prompt_note: str | None = None

    def effective_packing_chars(self) -> int | None:
        from app.prompt_engine.capacity import OfficialPromptCapacity, packing_budget

        recommended = (
            self.recommended_max_prompt_chars
            if self.recommended_max_prompt_chars is not None
            else self.max_prompt_chars
        )
        official = OfficialPromptCapacity(
            self.official_max_prompt_chars,
            self.official_prompt_status,  # type: ignore[arg-type]
            self.official_prompt_note,
        )
        return packing_budget(recommended_max_chars=recommended, official=official)


@dataclass(frozen=True)
class ModelUiMeta:
    provider: str
    provider_label: str
    tasks: tuple[str, ...]
    docs_url: str | None = None
    pricing_note: str | None = None
    supports_edit: bool = True
    supports_i2i: bool = True
    supports_t2i: bool = False
    badge: str | None = None


@dataclass(frozen=True)
class ModelSpec:
    """Canonical definition for one fal endpoint."""

    endpoint_id: str
    display_name: str
    family: str
    category: str
    capabilities: dict[str, Any]
    input_schema: dict[str, Any]
    default_params: dict[str, Any]
    image: ImageContract
    ui: ModelUiMeta
    workflow_allowlist: list[str] | None = None
    sort_order: int = 100
    cost_per_call: float | None = None
    config_extra: dict[str, Any] = dc_field(default_factory=dict)
    builder_id: str = "generic"

    def to_seed_dict(self) -> dict[str, Any]:
        """Shape expected by seed_model_definitions / legacy FAL_MODELS consumers."""
        config: dict[str, Any] = {
            "image_field": self.image.image_field if self.image.mode != "none" else None,
            "min_images": self.image.min_images,
            "max_reference_images": self.image.max_images,
            "omit_prompt": self.image.omit_prompt,
            "prompt_field": self.image.prompt_field,
            "family": self.family,
            "builder_id": self.builder_id,
            "ui": {
                "provider": self.ui.provider,
                "provider_label": self.ui.provider_label,
                "tasks": list(self.ui.tasks),
                "docs_url": self.ui.docs_url,
                "pricing_note": self.ui.pricing_note or (f"${self.cost_per_call}/call" if self.cost_per_call else None),
                "supports_edit": self.ui.supports_edit,
                "supports_i2i": self.ui.supports_i2i,
                "supports_t2i": self.ui.supports_t2i,
                "badge": self.ui.badge,
                "max_images": self.image.max_images,
                "min_images": self.image.min_images,
                "max_prompt_chars": self.image.max_prompt_chars,
            },
            "limits": {
                "min_images": self.image.min_images,
                "max_images": self.image.max_images,
                # Packing budget used by composers / builders (recommended, clamped by official).
                "max_prompt_chars": self.image.effective_packing_chars(),
                "recommended_max_prompt_chars": self.image.recommended_max_prompt_chars
                or self.image.max_prompt_chars,
                "official_max_prompt_chars": self.image.official_max_prompt_chars,
                "official_prompt_status": self.image.official_prompt_status,
                "official_prompt_note": self.image.official_prompt_note,
            },
            **self.config_extra,
        }
        packing = self.image.effective_packing_chars()
        if packing is not None:
            config["max_prompt_chars"] = packing
        if self.image.recommended_max_prompt_chars is not None:
            config["recommended_max_prompt_chars"] = self.image.recommended_max_prompt_chars
        elif self.image.max_prompt_chars is not None:
            config["recommended_max_prompt_chars"] = self.image.max_prompt_chars
        if self.image.official_max_prompt_chars is not None:
            config["official_max_prompt_chars"] = self.image.official_max_prompt_chars
        if self.image.official_prompt_status:
            config["official_prompt_status"] = self.image.official_prompt_status
        if self.image.official_prompt_note:
            config["official_prompt_note"] = self.image.official_prompt_note
        # Keep ui.max_prompt_chars as packing budget for frontend BC
        config["ui"]["max_prompt_chars"] = packing
        config["ui"]["recommended_max_prompt_chars"] = config.get("recommended_max_prompt_chars")
        config["ui"]["official_max_prompt_chars"] = self.image.official_max_prompt_chars
        config["ui"]["official_prompt_status"] = self.image.official_prompt_status
        if self.image.mode == "try_on_fields":
            config["input_mode"] = "try_on"
            config["try_on_fields"] = dict(self.image.try_on_fields)
            config["product_image_index"] = self.image.product_image_index
            config["person_image_index"] = self.image.person_image_index
        elif self.image.mode == "try_on_ordered":
            config["input_mode"] = "try_on"
            config["try_on_image_order"] = list(self.image.try_on_image_order or ("person", "product"))
            config["image_field"] = self.image.image_field
        if self.image.reference_image_field:
            config["reference_image_field"] = self.image.reference_image_field
        if config.get("image_field") is None:
            config.pop("image_field", None)

        return {
            "endpoint_id": self.endpoint_id,
            "display_name": self.display_name,
            "category": self.category,
            "capabilities": dict(self.capabilities),
            "input_schema": self.input_schema,
            "default_params": dict(self.default_params),
            "workflow_allowlist": self.workflow_allowlist,
            "config": config,
            "sort_order": self.sort_order,
            "cost_per_call": self.cost_per_call,
        }


def infer_family(endpoint_id: str) -> str:
    eid = endpoint_id.lower()
    if "nano-banana" in eid or "gemini" in eid and "/edit" in eid:
        return "nano_banana"
    if "gpt-image" in eid:
        return "gpt_image"
    if "kontext" in eid:
        return "flux_kontext"
    if "flux-2" in eid and ("edit" in eid or "max" in eid):
        return "flux2_edit"
    if "seedream" in eid:
        return "seedream"
    if "grok" in eid:
        return "grok"
    if any(x in eid for x in ("tryon", "try-on", "vton", "cat-vton", "leffa", "fashn", "lucy2")):
        return "vton"
    if "flux/schnell" in eid or eid.endswith("/flux-2-pro") or eid.endswith("flux-2-pro"):
        return "t2i"
    if "flux" in eid:
        return "flux_i2i"
    return "generic"


def infer_builder_id(endpoint_id: str, config: dict[str, Any]) -> str:
    if config.get("input_mode") == "try_on":
        return "vton"
    family = infer_family(endpoint_id)
    if family in {"nano_banana", "gpt_image", "flux_kontext", "flux2_edit", "seedream", "grok", "t2i", "flux_i2i"}:
        return family
    return "generic"


def image_contract_from_seed(config: dict[str, Any], capabilities: dict[str, Any]) -> ImageContract:
    recommended = config.get("recommended_max_prompt_chars")
    if recommended is None:
        recommended = config.get("max_prompt_chars")

    official_max = config.get("official_max_prompt_chars")
    official_status = str(config.get("official_prompt_status") or "undocumented")
    official_note = config.get("official_prompt_note")

    if config.get("input_mode") == "try_on":
        try_on_fields = config.get("try_on_fields") or {}
        if try_on_fields:
            return ImageContract(
                mode="try_on_fields",
                image_field="image_urls",
                min_images=int(config.get("min_images", 2)),
                max_images=int(config.get("max_reference_images", 2)),
                try_on_fields=dict(try_on_fields),
                product_image_index=int(config.get("product_image_index", 0)),
                person_image_index=int(config.get("person_image_index", 1)),
                omit_prompt=bool(config.get("omit_prompt")),
                prompt_field=str(config.get("prompt_field") or "prompt"),
                max_prompt_chars=recommended,
                recommended_max_prompt_chars=recommended,
                official_max_prompt_chars=official_max,
                official_prompt_status=official_status,
                official_prompt_note=official_note,
            )
        return ImageContract(
            mode="try_on_ordered",
            image_field=str(config.get("image_field") or "image_urls"),
            min_images=int(config.get("min_images", 2)),
            max_images=int(config.get("max_reference_images", 4)),
            try_on_image_order=tuple(config.get("try_on_image_order") or ["person", "product"]),
            omit_prompt=bool(config.get("omit_prompt")),
            prompt_field=str(config.get("prompt_field") or "prompt"),
            max_prompt_chars=recommended,
            recommended_max_prompt_chars=recommended,
            official_max_prompt_chars=official_max,
            official_prompt_status=official_status,
            official_prompt_note=official_note,
        )

    if not capabilities.get("requires_image", True) and not capabilities.get("image_to_image"):
        return ImageContract(
            mode="none",
            min_images=0,
            max_images=0,
            omit_prompt=False,
            max_prompt_chars=recommended,
            recommended_max_prompt_chars=recommended,
            official_max_prompt_chars=official_max,
            official_prompt_status=official_status,
            official_prompt_note=official_note,
        )

    field = str(config.get("image_field") or "image_urls")
    mode: ImageMode = "single_url" if field == "image_url" else "urls_array"
    return ImageContract(
        mode=mode,
        image_field=field,
        min_images=int(config.get("min_images", 1 if capabilities.get("requires_image", True) else 0)),
        max_images=int(config.get("max_reference_images", 14)),
        reference_image_field=config.get("reference_image_field"),
        omit_prompt=bool(config.get("omit_prompt")),
        prompt_field=str(config.get("prompt_field") or "prompt"),
        max_prompt_chars=recommended,
        recommended_max_prompt_chars=recommended,
        official_max_prompt_chars=official_max,
        official_prompt_status=official_status,
        official_prompt_note=official_note,
    )


def _enrich_prompt_capacity(image: ImageContract, *, family: str, endpoint_id: str) -> ImageContract:
    """Fill official/recommended capacities from family tables when seed omits them."""
    from types import SimpleNamespace

    from app.prompt_engine.capacity import resolve_official_capacity
    from app.prompt_engine.profiles import DEFAULT_PROFILE, _FAMILY_PROFILES

    stub = SimpleNamespace(endpoint_id=endpoint_id, family=family, image=image)
    official = resolve_official_capacity(stub)  # type: ignore[arg-type]
    profile = _FAMILY_PROFILES.get(family, DEFAULT_PROFILE)
    eid = endpoint_id.lower()
    if "ideogram" in eid:
        profile = _FAMILY_PROFILES["ideogram"]
    elif "recraft" in eid:
        profile = _FAMILY_PROFILES["recraft"]
    elif "imagen" in eid:
        profile = _FAMILY_PROFILES["imagen"]

    recommended = image.recommended_max_prompt_chars
    if recommended is None:
        recommended = image.max_prompt_chars
    if recommended is None:
        recommended = profile.max_chars

    official_max = image.official_max_prompt_chars
    official_status = image.official_prompt_status
    official_note = image.official_prompt_note
    if official_max is None and image.official_prompt_status == "undocumented":
        official_max = official.max_chars
        official_status = official.status
        official_note = official.note

    return ImageContract(
        mode=image.mode,
        image_field=image.image_field,
        min_images=image.min_images,
        max_images=image.max_images,
        roles=image.roles,
        try_on_fields=image.try_on_fields,
        try_on_image_order=image.try_on_image_order,
        product_image_index=image.product_image_index,
        person_image_index=image.person_image_index,
        reference_image_field=image.reference_image_field,
        omit_prompt=image.omit_prompt,
        prompt_field=image.prompt_field,
        max_prompt_chars=recommended,
        recommended_max_prompt_chars=recommended,
        official_max_prompt_chars=official_max,
        official_prompt_status=official_status,
        official_prompt_note=official_note,
    )


def provider_from_endpoint(endpoint_id: str) -> tuple[str, str]:
    eid = endpoint_id.lower()
    if eid.startswith("openai/") or "gpt-image" in eid:
        return "openai", "OpenAI"
    if "nano-banana" in eid or "gemini" in eid:
        return "google", "Google"
    if "flux" in eid or "bfl" in eid:
        return "bfl", "Black Forest Labs"
    if "seedream" in eid or "bytedance" in eid:
        return "bytedance", "ByteDance"
    if "grok" in eid or eid.startswith("xai/"):
        return "xai", "xAI"
    if "kling" in eid:
        return "kling", "Kling AI"
    if "fashn" in eid:
        return "fashn", "FASHN"
    if "ideogram" in eid:
        return "ideogram", "Ideogram"
    if "recraft" in eid:
        return "recraft", "Recraft"
    return "fal", "fal.ai"


def model_spec_from_seed_dict(spec: dict[str, Any]) -> ModelSpec:
    config = dict(spec.get("config") or {})
    caps = dict(spec.get("capabilities") or {})
    endpoint_id = spec["endpoint_id"]
    family = str(config.get("family") or infer_family(endpoint_id))
    builder_id = str(config.get("builder_id") or infer_builder_id(endpoint_id, config))
    provider, provider_label = provider_from_endpoint(endpoint_id)
    image = image_contract_from_seed(config, caps)
    image = _enrich_prompt_capacity(image, family=family, endpoint_id=endpoint_id)

    tasks: list[str] = []
    if caps.get("image_to_image"):
        tasks.append("I2I")
    if caps.get("text_to_image"):
        tasks.append("T2I")
    if caps.get("virtual_try_on"):
        tasks.append("VTON")
    if not tasks:
        tasks.append("Edit")

    info = config.get("model_info") or {}
    ui = ModelUiMeta(
        provider=provider,
        provider_label=provider_label,
        tasks=tuple(tasks),
        docs_url=info.get("docs_url") if isinstance(info, dict) else None,
        pricing_note=info.get("pricing") if isinstance(info, dict) else None,
        supports_edit=bool(caps.get("image_to_image")),
        supports_i2i=bool(caps.get("image_to_image")),
        supports_t2i=bool(caps.get("text_to_image")),
        badge="VTON" if caps.get("virtual_try_on") else ("T2I" if caps.get("text_to_image") and not caps.get("image_to_image") else "I2I"),
    )

    # Keep enrich keys that builders don't own
    reserved = {
        "image_field",
        "min_images",
        "max_reference_images",
        "omit_prompt",
        "prompt_field",
        "family",
        "builder_id",
        "ui",
        "limits",
        "input_mode",
        "try_on_fields",
        "try_on_image_order",
        "product_image_index",
        "person_image_index",
        "reference_image_field",
        "max_prompt_chars",
    }
    extra = {k: v for k, v in config.items() if k not in reserved}

    return ModelSpec(
        endpoint_id=endpoint_id,
        display_name=spec["display_name"],
        family=family,
        category=spec.get("category") or "image_to_image",
        capabilities=caps,
        input_schema=spec.get("input_schema") or {"type": "object", "properties": {}},
        default_params=dict(spec.get("default_params") or {}),
        image=image,
        ui=ui,
        workflow_allowlist=spec.get("workflow_allowlist"),
        sort_order=int(spec.get("sort_order", 100)),
        cost_per_call=spec.get("cost_per_call"),
        config_extra=extra,
        builder_id=builder_id,
    )
