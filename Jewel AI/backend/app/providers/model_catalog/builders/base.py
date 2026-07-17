"""Family request builders — each ModelSpec picks a builder_id."""

from __future__ import annotations

from typing import Any, Protocol

from app.models import ModelDefinition
from app.providers.model_catalog.spec import SYSTEM_FIELDS, ImageContract, ModelSpec
from app.providers.types import GenerationRequest


def truncate_prompt(text: str, limit: int | None) -> str:
    if not text or not limit or len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in (". ", "; ", "\n", " "):
        idx = cut.rfind(sep)
        if idx > limit * 0.7:
            return cut[: idx + len(sep)].rstrip()
    return cut.rstrip(".,; ") + "…"


def aspect_to_gpt_size(aspect: str) -> str:
    mapping = {
        "1:1": "1024x1024",
        "16:9": "1536x1024",
        "9:16": "1024x1536",
        "4:3": "1536x1024",
        "3:4": "1024x1536",
    }
    return mapping.get(aspect, "auto")


def aspect_to_image_size(aspect: str) -> str:
    mapping = {
        "1:1": "square_hd",
        "16:9": "landscape_16_9",
        "9:16": "portrait_16_9",
        "3:4": "portrait_4_3",
        "4:3": "landscape_4_3",
    }
    return mapping.get(aspect, "square_hd")


class RequestBuilder(Protocol):
    builder_id: str

    def build(
        self,
        request: GenerationRequest,
        fal_image_urls: list[str],
        *,
        spec: ModelSpec | None = None,
        model_def: ModelDefinition | None = None,
    ) -> dict[str, Any]:
        ...


def _resolve_image_at(urls: list[str], index: int) -> str:
    if index < len(urls):
        return urls[index]
    return urls[0]


def _merge_params(spec: ModelSpec | None, model_def: ModelDefinition | None, request: GenerationRequest) -> dict[str, Any]:
    defaults = dict((spec.default_params if spec else None) or (model_def.default_params if model_def else {}) or {})
    user = dict(request.model_params or {})
    merged = {**defaults, **user}

    schema = (spec.input_schema if spec else None) or (model_def.input_schema if model_def else {}) or {}
    schema_props = schema.get("properties") or {}
    config = (spec.to_seed_dict()["config"] if spec else None) or (model_def.config if model_def else {}) or {}

    if request.aspect_ratio:
        if "aspect_ratio" in schema_props and "aspect_ratio" not in merged:
            merged["aspect_ratio"] = request.aspect_ratio
        elif "image_size" in schema_props and "image_size" not in merged:
            size_enum = schema_props.get("image_size", {}).get("enum") or []
            if "1024x1024" in size_enum or "auto" in size_enum:
                merged["image_size"] = aspect_to_gpt_size(request.aspect_ratio)
            else:
                merged["image_size"] = aspect_to_image_size(request.aspect_ratio)

    if request.number_of_images:
        aliases = config.get("param_aliases") or {}
        count = request.number_of_images
        if "num_images" in schema_props:
            merged["num_images"] = count
        elif "num_samples" in schema_props:
            merged["num_samples"] = count
        else:
            for src, dest in aliases.items():
                if src == "number_of_images":
                    merged[dest] = count
            if "num_images" not in merged and "num_samples" not in merged:
                merged["num_images"] = count

    for src, dest in (config.get("param_aliases") or {}).items():
        if src == "number_of_images":
            continue
        if src in merged and dest not in merged:
            merged[dest] = merged.pop(src)

    return {k: v for k, v in merged.items() if v is not None and v != "" and k not in SYSTEM_FIELDS}


def _strip_unknown(args: dict[str, Any], schema_props: dict[str, Any]) -> None:
    allowed = set(schema_props.keys()) | SYSTEM_FIELDS
    for key in list(args.keys()):
        if key not in allowed:
            args.pop(key, None)


def _apply_images(args: dict[str, Any], contract: ImageContract, fal_image_urls: list[str]) -> None:
    if contract.mode == "none":
        return

    if not fal_image_urls and contract.min_images > 0:
        raise ValueError("This model requires an input image - upload a product photo first.")

    if len(fal_image_urls) < contract.min_images:
        raise ValueError(
            f"This model requires at least {contract.min_images} image(s); received {len(fal_image_urls)}."
        )
    if contract.max_images and len(fal_image_urls) > contract.max_images:
        fal_image_urls = fal_image_urls[: contract.max_images]

    if contract.mode == "try_on_fields":
        args[contract.try_on_fields["person"]] = _resolve_image_at(fal_image_urls, contract.person_image_index)
        args[contract.try_on_fields["product"]] = _resolve_image_at(fal_image_urls, contract.product_image_index)
        args.pop("image_url", None)
        args.pop("image_urls", None)
        return

    if contract.mode == "try_on_ordered":
        order = contract.try_on_image_order or ("person", "product")
        ordered: list[str] = []
        for role in order:
            if role == "person":
                ordered.append(_resolve_image_at(fal_image_urls, contract.person_image_index))
            else:
                ordered.append(_resolve_image_at(fal_image_urls, contract.product_image_index))
        if contract.image_field == "image_urls":
            args["image_urls"] = ordered
            args.pop("image_url", None)
        else:
            args["image_url"] = ordered[0]
            args.pop("image_urls", None)
        return

    if contract.mode == "urls_array":
        args["image_urls"] = fal_image_urls
        args.pop("image_url", None)
        return

    # single_url
    args["image_url"] = fal_image_urls[0]
    args.pop("image_urls", None)
    if contract.reference_image_field and len(fal_image_urls) > 1:
        args[contract.reference_image_field] = fal_image_urls[1]


class SpecRequestBuilder:
    """Default builder driven entirely by ModelSpec.image contract."""

    builder_id = "generic"

    def build(
        self,
        request: GenerationRequest,
        fal_image_urls: list[str],
        *,
        spec: ModelSpec | None = None,
        model_def: ModelDefinition | None = None,
    ) -> dict[str, Any]:
        if spec is None and model_def is not None:
            from app.providers.model_catalog.spec import model_spec_from_seed_dict

            spec = model_spec_from_seed_dict(
                {
                    "endpoint_id": model_def.endpoint_id,
                    "display_name": model_def.display_name,
                    "category": model_def.category,
                    "capabilities": model_def.capabilities or {},
                    "input_schema": model_def.input_schema or {},
                    "default_params": model_def.default_params or {},
                    "workflow_allowlist": model_def.workflow_allowlist,
                    "config": model_def.config or {},
                    "sort_order": model_def.sort_order,
                    "cost_per_call": model_def.cost_per_call,
                }
            )
        if spec is None:
            raise ValueError("ModelSpec is required to build fal arguments")

        contract = spec.image
        if not contract.omit_prompt and (not request.prompt or not request.prompt.strip()):
            raise ValueError("A prompt is required for image generation.")

        args: dict[str, Any] = {}
        packing = contract.effective_packing_chars()
        if not contract.omit_prompt:
            args[contract.prompt_field] = truncate_prompt(request.prompt, packing)

        schema_props = (spec.input_schema or {}).get("properties", {})
        if request.negative_prompt and (not schema_props or "negative_prompt" in schema_props):
            args["negative_prompt"] = truncate_prompt(request.negative_prompt, packing)

        args.update(_merge_params(spec, model_def, request))
        _apply_images(args, contract, list(fal_image_urls))
        if schema_props:
            _strip_unknown(args, schema_props)
        return args


class NanoBananaBuilder(SpecRequestBuilder):
    builder_id = "nano_banana"


class GptImageBuilder(SpecRequestBuilder):
    builder_id = "gpt_image"


class FluxKontextBuilder(SpecRequestBuilder):
    builder_id = "flux_kontext"


class Flux2EditBuilder(SpecRequestBuilder):
    builder_id = "flux2_edit"


class SeedreamBuilder(SpecRequestBuilder):
    builder_id = "seedream"


class GrokBuilder(SpecRequestBuilder):
    builder_id = "grok"


class FluxI2IBuilder(SpecRequestBuilder):
    builder_id = "flux_i2i"


class VtonBuilder(SpecRequestBuilder):
    builder_id = "vton"


class T2IBuilder(SpecRequestBuilder):
    """Text-to-image: images optional."""

    builder_id = "t2i"

    def build(
        self,
        request: GenerationRequest,
        fal_image_urls: list[str],
        *,
        spec: ModelSpec | None = None,
        model_def: ModelDefinition | None = None,
    ) -> dict[str, Any]:
        if spec is None:
            raise ValueError("ModelSpec is required")
        if not request.prompt or not request.prompt.strip():
            raise ValueError("A prompt is required for image generation.")
        args: dict[str, Any] = {
            spec.image.prompt_field: truncate_prompt(request.prompt, spec.image.effective_packing_chars()),
        }
        args.update(_merge_params(spec, model_def, request))
        if fal_image_urls and spec.image.mode != "none":
            _apply_images(args, spec.image, list(fal_image_urls))
        schema_props = (spec.input_schema or {}).get("properties", {})
        if schema_props:
            _strip_unknown(args, schema_props)
        return args


_BUILDERS: dict[str, RequestBuilder] = {
    b.builder_id: b
    for b in (
        SpecRequestBuilder(),
        NanoBananaBuilder(),
        GptImageBuilder(),
        FluxKontextBuilder(),
        Flux2EditBuilder(),
        SeedreamBuilder(),
        GrokBuilder(),
        FluxI2IBuilder(),
        VtonBuilder(),
        T2IBuilder(),
    )
}


def get_builder(builder_id: str | None) -> RequestBuilder:
    return _BUILDERS.get(builder_id or "generic") or _BUILDERS["generic"]


def build_arguments(
    request: GenerationRequest,
    fal_image_urls: list[str],
    *,
    spec: ModelSpec | None = None,
    model_def: ModelDefinition | None = None,
    endpoint: str | None = None,
) -> dict[str, Any]:
    if spec is None and endpoint:
        from app.providers.model_catalog.registry import get_spec

        spec = get_spec(endpoint)
    builder_id = (spec.builder_id if spec else None) or "generic"
    return get_builder(builder_id).build(request, fal_image_urls, spec=spec, model_def=model_def)
