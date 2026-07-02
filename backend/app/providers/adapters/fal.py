import asyncio
from pathlib import Path
from typing import Any

import httpx
from fal_client import SyncClient

from app.config import get_settings
from app.logging_config import get_logger
from app.models import ModelDefinition
from app.providers.fal_response import extract_image_urls
from app.providers.fal_upload import (
    fetch_and_upload_to_fal,
    upload_bytes_to_fal,
    upload_file_to_fal,
)
from app.providers.types import GenerationRequest, GenerationResult, ModelCapabilities, ProviderStatus
from app.storage.local import storage

logger = get_logger(__name__)
settings = get_settings()
FETCH_TIMEOUT = 120.0
FAL_CLIENT_TIMEOUT = 600.0
SYSTEM_FIELDS = {
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


def _truncate_prompt(text: str, model_def: ModelDefinition | None) -> str:
    if not text or not model_def:
        return text
    limit = (model_def.config or {}).get("max_prompt_chars")
    if not limit or len(text) <= limit:
        return text
    trimmed = text[:limit].rsplit(" ", 1)[0] if limit > 20 else text[:limit]
    return trimmed.rstrip(".,; ") + "…"


def _client(api_key: str) -> SyncClient:
    return SyncClient(key=api_key, default_timeout=120.0)


def _resolve_local_path(url: str) -> Path | None:
    path = storage.resolve_path(url)
    if path and path.exists():
        return path
    return None


def _upload_to_fal(local_path: Path, api_key: str) -> str:
    return upload_file_to_fal(local_path, api_key)


def _is_fal_cdn_url(url: str) -> bool:
    return url.startswith("https://") and ("fal.media" in url or "fal-cdn" in url or "fal.ai" in url)


async def _ensure_fal_url(url: str, api_key: str) -> str:
    """Resolve job input images to fal CDN URLs (object storage, local file, or public fetch)."""
    if _is_fal_cdn_url(url):
        return url

    blob = storage.read_bytes_by_url(url)
    if blob is not None:
        ext = Path(url).suffix.lower()
        content_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(
            ext, "image/jpeg"
        )
        return await asyncio.to_thread(upload_bytes_to_fal, blob, content_type, api_key)

    if url.startswith("http://") or url.startswith("https://"):
        local = _resolve_local_path(url)
        if local:
            return await asyncio.to_thread(_upload_to_fal, local, api_key)
        return await fetch_and_upload_to_fal(url, api_key)

    local = _resolve_local_path(url)
    if local:
        return await asyncio.to_thread(_upload_to_fal, local, api_key)

    public_url = storage.public_url(url)
    if public_url != url:
        try:
            return await fetch_and_upload_to_fal(public_url, api_key)
        except Exception as exc:
            raise ValueError(f"Cannot resolve input image: {url} (fetch failed for {public_url})") from exc

    raise ValueError(f"Cannot resolve input image: {url}")


def _aspect_to_gpt_size(aspect: str) -> str:
    mapping = {
        "1:1": "1024x1024",
        "16:9": "1536x1024",
        "9:16": "1024x1536",
        "4:3": "1536x1024",
        "3:4": "1024x1536",
    }
    return mapping.get(aspect, "auto")


def _aspect_to_image_size(aspect: str) -> str:
    mapping = {
        "1:1": "square_hd",
        "16:9": "landscape_16_9",
        "9:16": "portrait_16_9",
        "3:4": "portrait_4_3",
        "4:3": "landscape_4_3",
    }
    return mapping.get(aspect, "square_hd")


def _merge_params(model_def: ModelDefinition | None, request: GenerationRequest) -> dict[str, Any]:
    defaults = dict(model_def.default_params if model_def else {})
    user = dict(request.model_params or {})
    merged = {**defaults, **user}

    schema_props = (model_def.input_schema or {}).get("properties", {}) if model_def else {}

    if request.aspect_ratio:
        if "aspect_ratio" in schema_props and "aspect_ratio" not in merged:
            merged["aspect_ratio"] = request.aspect_ratio
        elif "image_size" in schema_props and "image_size" not in merged:
            size_enum = schema_props.get("image_size", {}).get("enum") or []
            if "1024x1024" in size_enum or "auto" in size_enum:
                merged["image_size"] = _aspect_to_gpt_size(request.aspect_ratio)
            else:
                merged["image_size"] = _aspect_to_image_size(request.aspect_ratio)

    if request.number_of_images:
        aliases = (model_def.config or {}).get("param_aliases") or {} if model_def else {}
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

    config = (model_def.config or {}) if model_def else {}
    for src, dest in (config.get("param_aliases") or {}).items():
        if src == "number_of_images":
            continue
        if src in merged and dest not in merged:
            merged[dest] = merged.pop(src)

    return {k: v for k, v in merged.items() if v is not None and v != "" and k not in SYSTEM_FIELDS}


def _image_input_field(model_def: ModelDefinition | None, endpoint: str) -> str:
    if model_def:
        config = model_def.config or {}
        if config.get("image_field"):
            return str(config["image_field"])
    raise ValueError(f"No image_field config for endpoint: {endpoint}")


def _strip_unknown_params(args: dict[str, Any], schema_props: dict, extra_fields: set[str] | None = None) -> None:
    """Keep only params defined in the model schema plus required image/prompt fields."""
    allowed = set(schema_props.keys()) | SYSTEM_FIELDS | (extra_fields or set())
    for key in list(args.keys()):
        if key not in allowed:
            args.pop(key, None)


def _resolve_image_at(fal_image_urls: list[str], index: int) -> str:
    if index < len(fal_image_urls):
        return fal_image_urls[index]
    return fal_image_urls[0]


def _apply_try_on_inputs(
    args: dict[str, Any],
    model_def: ModelDefinition | None,
    fal_image_urls: list[str],
) -> None:
    config = (model_def.config or {}) if model_def else {}
    min_images = int(config.get("min_images", 2))
    if len(fal_image_urls) < min_images:
        raise ValueError(
            f"This model requires {min_images} images (product + model portrait). "
            "Upload jewelry and a reference portrait."
        )

    try_on_fields = config.get("try_on_fields") or {}
    if try_on_fields:
        person_idx = int(config.get("person_image_index", 1))
        product_idx = int(config.get("product_image_index", 0))
        args[try_on_fields["person"]] = _resolve_image_at(fal_image_urls, person_idx)
        args[try_on_fields["product"]] = _resolve_image_at(fal_image_urls, product_idx)
        args.pop("image_url", None)
        args.pop("image_urls", None)
        return

    order = config.get("try_on_image_order") or ["person", "product"]
    field = config.get("image_field", "image_urls")
    ordered_urls: list[str] = []
    for role in order:
        if role == "person":
            ordered_urls.append(_resolve_image_at(fal_image_urls, int(config.get("person_image_index", 1))))
        else:
            ordered_urls.append(_resolve_image_at(fal_image_urls, int(config.get("product_image_index", 0))))
    if field == "image_urls":
        args["image_urls"] = ordered_urls
        args.pop("image_url", None)
    else:
        args["image_url"] = ordered_urls[0]
        args.pop("image_urls", None)


def _apply_image_inputs(
    args: dict[str, Any],
    model_def: ModelDefinition | None,
    endpoint: str,
    fal_image_urls: list[str],
) -> None:
    config = (model_def.config or {}) if model_def else {}
    if config.get("input_mode") == "try_on":
        _apply_try_on_inputs(args, model_def, fal_image_urls)
        return

    field = _image_input_field(model_def, endpoint)
    if field == "image_urls":
        args["image_urls"] = fal_image_urls
        args.pop("image_url", None)
    else:
        args["image_url"] = fal_image_urls[0]
        args.pop("image_urls", None)
        ref_field = config.get("reference_image_field")
        if ref_field and len(fal_image_urls) > 1:
            args[ref_field] = fal_image_urls[1]


def _build_arguments(
    request: GenerationRequest,
    model_def: ModelDefinition | None,
    endpoint: str,
    fal_image_urls: list[str],
) -> dict[str, Any]:
    config = (model_def.config or {}) if model_def else {}
    omit_prompt = bool(config.get("omit_prompt"))
    prompt_field = str(config.get("prompt_field") or "prompt")

    if not omit_prompt and (not request.prompt or not request.prompt.strip()):
        raise ValueError("A prompt is required for image generation.")
    if not fal_image_urls:
        raise ValueError("This model requires an input image - upload a product photo first.")

    args: dict[str, Any] = {}
    if not omit_prompt:
        args[prompt_field] = _truncate_prompt(request.prompt, model_def)
    schema_props = (model_def.input_schema or {}).get("properties", {}) if model_def else {}
    if request.negative_prompt and (not schema_props or "negative_prompt" in schema_props):
        args["negative_prompt"] = _truncate_prompt(request.negative_prompt, model_def)

    params = _merge_params(model_def, request)
    args.update(params)

    _apply_image_inputs(args, model_def, endpoint, fal_image_urls)

    if schema_props:
        _strip_unknown_params(args, schema_props)

    return args


class FalAdapter:
    name = "FAL"
    capabilities = ModelCapabilities(
        text_to_image=False,
        image_to_image=True,
        person_generation=True,
        material_accuracy=True,
    )

    def __init__(self, api_key: str, model_name: str | None = None) -> None:
        self.api_key = api_key
        self.model_name = model_name or "fal-ai/flux-pro/kontext"

    async def generate(
        self,
        request: GenerationRequest,
        model_def: ModelDefinition | None = None,
        db=None,
    ) -> GenerationResult:
        endpoint = request.model_endpoint_id or self.model_name

        fal_urls: list[str] = []
        for url in request.image_urls:
            fal_url = await _ensure_fal_url(url, self.api_key)
            fal_urls.append(fal_url)

        arguments = _build_arguments(request, model_def, endpoint, fal_urls)
        logger.info(
            "fal.ai request",
            extra={
                "extra_fields": {
                    "endpoint": endpoint,
                    "arg_keys": list(arguments.keys()),
                    "image_count": len(fal_urls),
                }
            },
        )

        client = _client(self.api_key)

        is_local = "localhost" in settings.api_public_url or "127.0.0.1" in settings.api_public_url
        webhook_url = None
        if request.job_id and not is_local:
            from app.auth.security import create_webhook_token

            webhook_token = create_webhook_token(request.job_id)
            webhook_url = (
                f"{settings.api_public_url.rstrip('/')}/api/providers/fal/webhook/{request.job_id}"
                f"?token={webhook_token}"
            )

        def _run() -> Any:
            if is_local or not webhook_url:
                return client.subscribe(
                    endpoint,
                    arguments=arguments,
                    with_logs=True,
                    client_timeout=FAL_CLIENT_TIMEOUT,
                )
            else:
                return client.submit(
                    endpoint,
                    arguments=arguments,
                    webhook_url=webhook_url,
                )

        try:
            result = await asyncio.to_thread(_run)
        except Exception as exc:
            raise RuntimeError(f"fal.ai call failed ({endpoint}): {exc}") from exc

        if not is_local and webhook_url:
            req_id = result.request_id if hasattr(result, "request_id") else (result.get("request_id") if isinstance(result, dict) else str(result))
            cost = model_def.cost_per_call if model_def and model_def.cost_per_call else 0.1
            return GenerationResult(
                image_bytes=None,
                provider=self.name,
                model=endpoint,
                cost=cost,
                usage={"endpoint": endpoint, "arguments_keys": list(arguments.keys()), "request_id": req_id},
                metadata={"fal_request_id": req_id},
                is_webhook_pending=True,
            )

        config = (model_def.config or {}) if model_def else {}
        img_urls = extract_image_urls(result if isinstance(result, dict) else {}, config)
        if not img_urls:
            raise RuntimeError(
                f"fal.ai returned no images for {endpoint}. "
                f"Response keys: {list(result.keys()) if isinstance(result, dict) else type(result)}"
            )

        all_bytes: list[bytes] = []
        async with httpx.AsyncClient(timeout=FETCH_TIMEOUT) as http:
            for img_url in img_urls:
                resp = await http.get(img_url)
                resp.raise_for_status()
                all_bytes.append(resp.content)

        cost = model_def.cost_per_call if model_def and model_def.cost_per_call else 0.1
        return GenerationResult(
            image_bytes=all_bytes[0] if all_bytes else None,
            provider=self.name,
            model=endpoint,
            cost=cost,
            usage={"endpoint": endpoint, "arguments_keys": list(arguments.keys()), "image_count": len(all_bytes)},
            metadata={
                "fal_result_keys": list(result.keys()) if isinstance(result, dict) else [],
                "all_image_urls": img_urls,
                "all_image_bytes": all_bytes[1:] if len(all_bytes) > 1 else [],
            },
        )

    async def health_check(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus(healthy=False, message="FAL_KEY not configured")
        return ProviderStatus(healthy=True, message="fal.ai API key configured")
