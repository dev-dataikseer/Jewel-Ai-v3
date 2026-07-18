"""Canonical image slot assembly for single and bulk generation jobs.

Order: product → theme|portrait → logo (when model capacity allows).
Logo falls back to post-compose when the model cannot accept another image.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.config import get_settings
from app.models import GenerationJob
from app.providers.model_catalog.spec import ImageContract, ModelSpec

LogoMode = Literal["model", "compose", "omit"]
ImageRoleName = Literal["product", "theme", "portrait", "logo"]

TRY_ON_WORKFLOWS = frozenset({"JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"})


@dataclass(frozen=True)
class ImageRole:
    index: int  # 1-based for prompt attachment text
    role: ImageRoleName
    url: str


@dataclass
class ImagePacket:
    image_urls: list[str]
    roles: list[ImageRole]
    logo_mode: LogoMode
    logo_url: str | None = None
    has_product: bool = False
    has_style_reference: bool = False
    has_portrait: bool = False
    has_logo: bool = False  # True when logo is included in fal image_urls
    max_images: int = 14
    debug: dict[str, Any] = field(default_factory=dict)

    def to_meta(self) -> dict[str, Any]:
        return {
            "imageRoles": [{"index": r.index, "role": r.role, "url": r.url} for r in self.roles],
            "logoMode": self.logo_mode,
            "logoApplied": self.logo_mode if self.logo_url else "none",
            "imagePacketDebug": self.debug,
        }

    def to_image_context_kwargs(self) -> dict[str, Any]:
        return {
            "has_product": self.has_product,
            "has_style_reference": self.has_style_reference,
            "has_portrait": self.has_portrait,
            "has_logo": self.has_logo,
            "image_count": len(self.image_urls) or 1,
            "roles": [{"index": r.index, "role": r.role} for r in self.roles],
        }


def _resolve_max_images(spec: ModelSpec | None, contract: ImageContract | None) -> int:
    if contract is None:
        return 14
    if contract.mode in ("none",):
        return 0
    if contract.mode == "single_url" and not contract.reference_image_field:
        return 1
    if contract.mode in ("try_on_fields", "try_on_ordered"):
        return max(1, int(contract.max_images or 2))
    return max(1, int(contract.max_images or 14))


def _dedupe(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def build_image_packet(
    job: GenerationJob,
    *,
    model_endpoint_id: str | None = None,
    model_spec: ModelSpec | None = None,
    logo_url: str | None = None,
    force_compose: bool | None = None,
) -> ImagePacket:
    """Build ordered fal image_urls + logo_mode for a generation job."""
    meta = job.provider_metadata or {}
    endpoint = model_endpoint_id or meta.get("modelEndpointId") or meta.get("modelName")
    spec = model_spec
    if spec is None and endpoint:
        from app.providers.model_catalog.registry import get_spec

        spec = get_spec(endpoint)
    contract = spec.image if spec else None
    max_images = _resolve_max_images(spec, contract)

    if force_compose is None:
        force_compose = bool(get_settings().logo_force_compose)

    product_url = job.input_url or None
    is_try_on = (job.workflow or "") in TRY_ON_WORKFLOWS
    portrait_url = None
    theme_url = None
    if is_try_on:
        portrait_url = job.model_url or job.reference_url or None
    else:
        theme_url = job.reference_url or None

    logo = logo_url if logo_url is not None else (meta.get("logoUrl") or None)
    if isinstance(logo, str):
        logo = logo.strip() or None
    else:
        logo = None

    slots: list[tuple[ImageRoleName, str]] = []
    if product_url:
        slots.append(("product", product_url))

    if portrait_url and portrait_url != product_url:
        slots.append(("portrait", portrait_url))
    elif theme_url and theme_url != product_url:
        slots.append(("theme", theme_url))

    # Capacity for model-input logo
    used = len(_dedupe([u for _, u in slots]))
    can_take_logo = bool(logo) and not force_compose and max_images > used
    if contract:
        if contract.mode == "none":
            can_take_logo = False
        elif contract.mode == "single_url" and not contract.reference_image_field:
            can_take_logo = False
        elif contract.mode in ("try_on_fields", "try_on_ordered") and used >= max_images:
            can_take_logo = False

    logo_mode: LogoMode = "omit"
    if logo:
        if can_take_logo:
            slots.append(("logo", logo))
            logo_mode = "model"
        else:
            logo_mode = "compose"

    deduped_slots: list[tuple[ImageRoleName, str]] = []
    seen_urls: set[str] = set()
    for role, url in slots:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped_slots.append((role, url))

    if max_images > 0 and len(deduped_slots) > max_images:
        truncated = deduped_slots[max_images:]
        deduped_slots = deduped_slots[:max_images]
        if logo and any(r == "logo" for r, _ in truncated):
            logo_mode = "compose"
            deduped_slots = [(r, u) for r, u in deduped_slots if r != "logo"]

    roles = [ImageRole(index=i + 1, role=role, url=url) for i, (role, url) in enumerate(deduped_slots)]
    urls = [r.url for r in roles]
    has_logo_in_model = any(r.role == "logo" for r in roles)
    if logo and logo_mode == "model" and not has_logo_in_model:
        logo_mode = "compose"

    return ImagePacket(
        image_urls=urls,
        roles=roles,
        logo_mode=logo_mode,
        logo_url=logo,
        has_product=any(r.role == "product" for r in roles) or bool(product_url),
        has_style_reference=any(r.role == "theme" for r in roles),
        has_portrait=any(r.role == "portrait" for r in roles),
        has_logo=has_logo_in_model,
        max_images=max_images,
        debug={
            "endpoint": endpoint,
            "contract_mode": contract.mode if contract else None,
            "max_images": max_images,
            "force_compose": force_compose,
            "workflow": job.workflow,
        },
    )


def apply_logo_compose_if_needed(
    image_bytes: bytes,
    *,
    logo_mode: LogoMode | str | None,
    logo_url: str | None,
    storage: Any,
) -> bytes:
    """Post-compose logo under the image only when logo_mode is compose."""
    if logo_mode != "compose" or not logo_url:
        return image_bytes
    from app.storage.logo_compose import composite_logo_beneath, load_logo_bytes_from_storage

    logo_bytes = load_logo_bytes_from_storage(logo_url, storage)
    if not logo_bytes:
        return image_bytes
    return composite_logo_beneath(image_bytes, logo_bytes)
