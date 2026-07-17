"""fal.ai adapter — orchestrates preprocess + model-specific request builders."""

from __future__ import annotations

import asyncio
from typing import Any

from fal_client import SyncClient

from app.config import get_settings
from app.logging_config import get_logger
from app.models import ModelDefinition
from app.providers.model_catalog.builders.base import _merge_params as _merge_params_impl
from app.providers.model_catalog.builders import build_arguments
from app.providers.model_catalog.preprocess import ensure_fal_url, prepare_images
from app.providers.model_catalog.registry import get_spec
from app.providers.model_catalog.response import parse_image_urls
from app.providers.model_catalog.spec import SYSTEM_FIELDS as SYSTEM_FIELDS
from app.providers.model_catalog.spec import model_spec_from_seed_dict
from app.providers.types import GenerationRequest, GenerationResult, ModelCapabilities, ProviderStatus

logger = get_logger(__name__)
settings = get_settings()
FETCH_TIMEOUT = 120.0
FAL_CLIENT_TIMEOUT = 600.0


def _client(api_key: str) -> SyncClient:
    return SyncClient(key=api_key, default_timeout=120.0)


def _spec_for(endpoint: str, model_def: ModelDefinition | None):
    spec = get_spec(endpoint)
    if spec:
        return spec
    if model_def:
        return model_spec_from_seed_dict(
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
    return None


# --- Legacy helpers kept for unit tests ---------------------------------

def _merge_params(model_def: ModelDefinition | None, request: GenerationRequest) -> dict:
    """Legacy helper for tests — merges defaults/user params via ModelSpec path."""
    endpoint = model_def.endpoint_id if model_def else ""
    spec = _spec_for(endpoint, model_def)
    return _merge_params_impl(spec, model_def, request)


def _image_input_field(model_def: ModelDefinition | None, endpoint: str) -> str:
    if model_def:
        config = model_def.config or {}
        if config.get("image_field"):
            return str(config["image_field"])
        spec = _spec_for(endpoint, model_def)
        if spec and spec.image.image_field:
            return spec.image.image_field
    raise ValueError(f"No image_field config for endpoint: {endpoint}")


def _build_arguments(
    request: GenerationRequest,
    model_def: ModelDefinition | None,
    endpoint: str,
    fal_image_urls: list[str],
) -> dict[str, Any]:
    return build_arguments(
        request,
        fal_image_urls,
        spec=_spec_for(endpoint, model_def),
        model_def=model_def,
        endpoint=endpoint,
    )


# Async upload helper used by older code paths / tests
_ensure_fal_url = ensure_fal_url


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
        spec = _spec_for(endpoint, model_def)

        if spec:
            prepared = await prepare_images(spec, list(request.image_urls or []), self.api_key)
            fal_urls = prepared.fal_urls
        else:
            fal_urls = []
            for url in request.image_urls or []:
                fal_urls.append(await ensure_fal_url(url, self.api_key))

        arguments = build_arguments(
            request,
            fal_urls,
            spec=spec,
            model_def=model_def,
            endpoint=endpoint,
        )
        logger.info(
            "fal.ai request",
            extra={
                "extra_fields": {
                    "endpoint": endpoint,
                    "family": spec.family if spec else None,
                    "builder": spec.builder_id if spec else None,
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
            req_id = (
                result.request_id
                if hasattr(result, "request_id")
                else (result.get("request_id") if isinstance(result, dict) else str(result))
            )
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
        img_urls = parse_image_urls(result if isinstance(result, dict) else {}, spec, config)
        if not img_urls:
            raise RuntimeError(
                f"fal.ai returned no images for {endpoint}. "
                f"Response keys: {list(result.keys()) if isinstance(result, dict) else type(result)}"
            )

        all_bytes: list[bytes] = []
        from app.security.url_fetch import safe_fetch_image_bytes

        for img_url in img_urls:
            all_bytes.append(await safe_fetch_image_bytes(img_url, timeout=FETCH_TIMEOUT))

        cost = model_def.cost_per_call if model_def and model_def.cost_per_call else (spec.cost_per_call if spec else 0.1)
        return GenerationResult(
            image_bytes=all_bytes[0] if all_bytes else None,
            provider=self.name,
            model=endpoint,
            cost=cost or 0.1,
            usage={"endpoint": endpoint, "arguments_keys": list(arguments.keys()), "image_count": len(all_bytes)},
            metadata={
                "fal_result_keys": list(result.keys()) if isinstance(result, dict) else [],
                "all_image_urls": img_urls,
                "all_image_bytes": all_bytes[1:] if len(all_bytes) > 1 else [],
                "family": spec.family if spec else None,
            },
        )

    async def health_check(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus(healthy=False, message="FAL_KEY not configured")
        return ProviderStatus(healthy=True, message="fal.ai API key configured")


def cancel_fal_request(endpoint: str, request_id: str, api_key: str | None = None) -> bool:
    """Best-effort cancel of a fal queue request. Returns True if cancel call succeeded."""
    key = api_key or settings.fal_key
    if not key or not request_id or not endpoint:
        return False
    try:
        client = _client(key)
        # fal_client SyncClient exposes cancel(request_id) on recent versions
        cancel = getattr(client, "cancel", None)
        if callable(cancel):
            cancel(endpoint, request_id)
            return True
    except TypeError:
        try:
            client = _client(key)
            client.cancel(request_id)  # type: ignore[attr-defined]
            return True
        except Exception as exc:
            logger.debug("fal cancel failed: %s", exc)
            return False
    except Exception as exc:
        logger.debug("fal cancel failed: %s", exc)
        return False

    # HTTP fallback for queue API
    try:
        import httpx

        url = f"https://queue.fal.run/{endpoint}/requests/{request_id}/cancel"
        resp = httpx.put(url, headers={"Authorization": f"Key {key}"}, timeout=15.0)
        return resp.status_code < 400
    except Exception as exc:
        logger.debug("fal cancel HTTP fallback failed: %s", exc)
        return False
