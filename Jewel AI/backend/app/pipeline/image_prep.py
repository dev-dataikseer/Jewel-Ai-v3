"""Robust per-model image preparation for fal.ai requests.

Takes user-uploaded / stored image URLs, builds a role-ordered packet matching
the selected model's ImageContract, then resolves each URL to a fal CDN URL.

Order of truth:
  1. build_image_packet — product → theme|portrait → logo (capacity-aware)
  2. validate_packet_for_contract — min/max + try-on requirements
  3. prepare_images — upload/cache to fal.media
  4. SpecRequestBuilder._apply_images — field mapping (image_urls vs image_url vs VTON fields)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.models import GenerationJob
from app.pipeline.image_packet import ImagePacket, build_image_packet
from app.providers.model_catalog.preprocess import PreparedImages, prepare_images, validate_image_count
from app.providers.model_catalog.spec import ImageContract, ModelSpec

logger = logging.getLogger(__name__)


@dataclass
class ModelImagePlan:
    """What the selected model will actually receive."""

    packet: ImagePacket
    fal_urls: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    contract_mode: str | None = None
    field_map: dict[str, str] = field(default_factory=dict)

    def to_debug(self) -> dict[str, Any]:
        return {
            "contract_mode": self.contract_mode,
            "fal_url_count": len(self.fal_urls),
            "roles": [{"index": r.index, "role": r.role} for r in self.packet.roles],
            "logo_mode": self.packet.logo_mode,
            "warnings": list(self.warnings),
            "field_map": dict(self.field_map),
            **(self.packet.debug or {}),
        }


def _field_map_for_contract(contract: ImageContract | None) -> dict[str, str]:
    if not contract:
        return {"mode": "unknown"}
    if contract.mode == "urls_array":
        return {"mode": "urls_array", "field": contract.image_field or "image_urls"}
    if contract.mode == "single_url":
        out = {"mode": "single_url", "field": contract.image_field or "image_url"}
        if contract.reference_image_field:
            out["reference_field"] = contract.reference_image_field
        return out
    if contract.mode == "try_on_fields":
        return {
            "mode": "try_on_fields",
            "person": (contract.try_on_fields or {}).get("person", ""),
            "product": (contract.try_on_fields or {}).get("product", ""),
            "person_index": str(contract.person_image_index),
            "product_index": str(contract.product_image_index),
        }
    if contract.mode == "try_on_ordered":
        return {
            "mode": "try_on_ordered",
            "field": contract.image_field or "image_urls",
            "order": ",".join(contract.try_on_image_order or ("person", "product")),
        }
    return {"mode": contract.mode}


def collect_packet_warnings(
    packet: ImagePacket,
    *,
    contract: ImageContract | None,
    job: GenerationJob,
) -> list[str]:
    """Human-readable notes when uploaded slots cannot all be sent to the model."""
    warnings: list[str] = []
    if not contract:
        return warnings

    theme = job.reference_url if (job.workflow or "") not in (
        "VIRTUAL_TRY_ON",
        "JEWELRY_ON_MODEL",
        "CUSTOMER_TRY_ON",
    ) else None
    portrait = job.model_url or (job.reference_url if (job.workflow or "") in (
        "VIRTUAL_TRY_ON",
        "JEWELRY_ON_MODEL",
        "CUSTOMER_TRY_ON",
    ) else None)
    logo = (job.provider_metadata or {}).get("logoUrl")

    if contract.mode == "single_url":
        if theme and not packet.has_style_reference:
            warnings.append(
                "This model accepts only one image (image_url). Theme/reference was not sent — "
                "use an image_urls model (Nano Banana Pro, GPT Image 2, FLUX 2) for theme+product."
            )
        if portrait and not packet.has_portrait:
            warnings.append(
                "This model accepts only one image. Portrait was not sent — use Nano Banana Pro "
                "or GPT Image 2 for jewelry-on-person compositing."
            )
        if logo and packet.logo_mode == "compose":
            warnings.append("Logo will be applied after generation (compose), not as a model reference.")

    if contract.mode in ("try_on_fields", "try_on_ordered"):
        if not packet.has_product or not packet.has_portrait:
            warnings.append("Virtual try-on models need both a product image and a person portrait.")

    if packet.logo_mode == "compose" and logo:
        warnings.append("Logo will be applied after generation (compose), not as a model reference.")

    dropped = (packet.debug or {}).get("dropped_slots") or []
    if dropped:
        warnings.append(
            f"Dropped slot(s) for this model's capacity: {', '.join(str(s) for s in dropped)}."
        )

    # Deduplicate identical messages
    seen: set[str] = set()
    out: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def validate_packet_for_contract(packet: ImagePacket, contract: ImageContract) -> None:
    """Raise ValueError if the packet cannot satisfy the model contract."""
    count = len(packet.image_urls)
    if contract.mode == "none":
        return
    validate_image_count(contract, count)
    if contract.mode in ("try_on_fields", "try_on_ordered") and count < 2:
        raise ValueError(
            "This try-on model needs two images: jewelry/product photo and a person portrait."
        )
    if contract.mode == "single_url" and count < 1:
        raise ValueError("Upload a product photo first — this model requires an input image.")


def build_model_image_plan(
    job: GenerationJob,
    *,
    model_spec: ModelSpec | None,
    model_endpoint_id: str | None = None,
    logo_url: str | None = None,
) -> ModelImagePlan:
    """Assemble + validate the image plan for a job/model (before fal upload)."""
    packet = build_image_packet(
        job,
        model_endpoint_id=model_endpoint_id,
        model_spec=model_spec,
        logo_url=logo_url,
    )
    contract = model_spec.image if model_spec else None
    warnings = collect_packet_warnings(packet, contract=contract, job=job)
    if contract:
        validate_packet_for_contract(packet, contract)
    return ModelImagePlan(
        packet=packet,
        warnings=warnings,
        contract_mode=contract.mode if contract else None,
        field_map=_field_map_for_contract(contract),
    )


async def prepare_job_images_for_model(
    job: GenerationJob,
    *,
    model_spec: ModelSpec,
    api_key: str,
    model_endpoint_id: str | None = None,
    logo_url: str | None = None,
) -> ModelImagePlan:
    """Full pipeline: packet → validate → fal CDN URLs."""
    plan = build_model_image_plan(
        job,
        model_spec=model_spec,
        model_endpoint_id=model_endpoint_id or model_spec.endpoint_id,
        logo_url=logo_url,
    )
    prepared: PreparedImages = await prepare_images(
        model_spec,
        plan.packet.image_urls,
        api_key,
        enforce_limits=True,
    )
    plan.fal_urls = list(prepared.fal_urls)
    if prepared.skipped:
        plan.warnings.append(f"Skipped unresolvable URLs: {prepared.skipped}")
    for w in plan.warnings:
        logger.info("image_prep[%s]: %s", job.id, w)
    return plan
