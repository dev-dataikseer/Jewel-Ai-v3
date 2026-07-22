"""fal.ai adapter — orchestrates preprocess + model-specific request builders."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fal_client import SyncClient

from app.config import get_settings
from app.logging_config import get_logger
from app.services.latency_trace import enabled as latency_trace_enabled
from app.services.latency_trace import log_event
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
        image_prep_ms: int | None = None

        if spec:
            prep_t0 = time.perf_counter()
            prepared = await prepare_images(spec, list(request.image_urls or []), self.api_key)
            fal_urls = prepared.fal_urls
            if latency_trace_enabled():
                image_prep_ms = int(round((time.perf_counter() - prep_t0) * 1000))
        else:
            fal_urls = []
            prep_t0 = time.perf_counter()
            for url in request.image_urls or []:
                fal_urls.append(await ensure_fal_url(url, self.api_key))
            if latency_trace_enabled():
                image_prep_ms = int(round((time.perf_counter() - prep_t0) * 1000))

        build_t0 = time.perf_counter()
        arguments = build_arguments(
            request,
            fal_urls,
            spec=spec,
            model_def=model_def,
            endpoint=endpoint,
        )
        build_args_ms: int | None = None
        if latency_trace_enabled():
            build_args_ms = int(round((time.perf_counter() - build_t0) * 1000))
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

        # Webhooks are optional. Prefer subscribe so the job finishes in-process
        # without depending on Celery finalize_fal_webhook (which some worker
        # images never registered, leaving Studio stuck on "Waiting on fal.ai").
        use_webhook = bool(getattr(settings, "fal_use_webhooks", False))
        is_local = "localhost" in settings.api_public_url or "127.0.0.1" in settings.api_public_url
        webhook_url = None
        if use_webhook and request.job_id and not is_local:
            from app.auth.security import create_webhook_token

            webhook_token = create_webhook_token(request.job_id)
            webhook_url = (
                f"{settings.api_public_url.rstrip('/')}/api/providers/fal/webhook/{request.job_id}"
                f"?token={webhook_token}"
            )

        def _run() -> Any:
            if webhook_url:
                return client.submit(
                    endpoint,
                    arguments=arguments,
                    webhook_url=webhook_url,
                )
            # Capture request_id via on_enqueue (subscribe result payload often omits it).
            captured: dict[str, str] = {}

            def _on_enqueue(request_id: str) -> None:
                if request_id:
                    captured["request_id"] = str(request_id)

            out = client.subscribe(
                endpoint,
                arguments=arguments,
                with_logs=False,
                client_timeout=FAL_CLIENT_TIMEOUT,
                on_enqueue=_on_enqueue,
            )
            if isinstance(out, dict) and captured.get("request_id"):
                out.setdefault("_fal_request_id", captured["request_id"])
            elif captured.get("request_id"):
                return {"_fal_wrapped_result": out, "_fal_request_id": captured["request_id"]}
            return out

        fal_http_t0 = time.perf_counter()
        try:
            result = await asyncio.to_thread(_run)
        except Exception as exc:
            if latency_trace_enabled():
                log_event(
                    "T2_fal_api_error",
                    job_id=request.job_id,
                    endpoint=endpoint,
                    fal_http_ms=int(round((time.perf_counter() - fal_http_t0) * 1000)),
                    error=str(exc)[:300],
                )
            raise RuntimeError(f"fal.ai call failed ({endpoint}): {exc}") from exc

        fal_http_ms = int(round((time.perf_counter() - fal_http_t0) * 1000))
        fal_mode = "webhook_submit" if webhook_url else "subscribe"
        if latency_trace_enabled():
            log_event(
                "T2_fal_api",
                job_id=request.job_id,
                endpoint=endpoint,
                fal_mode=fal_mode,
                T2_fal_api_ms=fal_http_ms,
                fal_image_prep_ms=image_prep_ms,
                fal_build_args_ms=build_args_ms,
                image_count=len(fal_urls),
                note=(
                    "webhook_submit = queue accept only; GPU time is in fal dashboard"
                    if webhook_url
                    else "subscribe = queue wait + GPU inside this call"
                ),
            )

        if webhook_url:
            req_id = (
                result.request_id
                if hasattr(result, "request_id")
                else (result.get("request_id") if isinstance(result, dict) else str(result))
            )
            logger.info(
                "fal webhook submit",
                extra={
                    "extra_fields": {
                        "job_id": request.job_id,
                        "fal_request_id": req_id,
                        "endpoint": endpoint,
                    }
                },
            )
            if latency_trace_enabled():
                log_event(
                    "T2_fal_request_id",
                    job_id=request.job_id,
                    fal_request_id=str(req_id) if req_id else None,
                    endpoint=endpoint,
                    T2_fal_api_ms=fal_http_ms,
                    fal_mode=fal_mode,
                )
            cost = model_def.cost_per_call if model_def and model_def.cost_per_call else 0.1
            return GenerationResult(
                image_bytes=None,
                provider=self.name,
                model=endpoint,
                cost=cost,
                usage={"endpoint": endpoint, "arguments_keys": list(arguments.keys()), "request_id": req_id},
                metadata={
                    "fal_request_id": req_id,
                    "latencyTrace": {
                        "T2_fal_api_ms": fal_http_ms,
                        "T2_fal_mode": fal_mode,
                        "fal_image_prep_ms": image_prep_ms,
                        "fal_build_args_ms": build_args_ms,
                    },
                },
                is_webhook_pending=True,
            )

        config = (model_def.config or {}) if model_def else {}
        # Unwrap optional request_id carrier from subscribe path
        subscribe_req_id = None
        if isinstance(result, dict):
            subscribe_req_id = result.pop("_fal_request_id", None) or result.get("request_id")
            if "_fal_wrapped_result" in result:
                result = result["_fal_wrapped_result"]

        parse_payload = result if isinstance(result, dict) else {}
        img_urls = parse_image_urls(parse_payload, spec, config)
        if not img_urls:
            raise RuntimeError(
                f"fal.ai returned no images for {endpoint}. "
                f"Response keys: {list(parse_payload.keys()) if isinstance(parse_payload, dict) else type(result)}"
            )

        from app.services.job_timing import extract_fal_inference_seconds

        inference_s = extract_fal_inference_seconds(parse_payload)

        logger.info(
            "fal subscribe complete",
            extra={
                "extra_fields": {
                    "job_id": request.job_id,
                    "endpoint": endpoint,
                    "image_count": len(img_urls),
                    "fal_request_id": subscribe_req_id,
                    "fal_inference_time": inference_s,
                }
            },
        )
        if latency_trace_enabled():
            log_event(
                "T2_fal_subscribe_complete",
                job_id=request.job_id,
                fal_request_id=str(subscribe_req_id) if subscribe_req_id else None,
                endpoint=endpoint,
                T2_fal_api_ms=fal_http_ms,
                fal_mode=fal_mode,
                fal_inference_time=inference_s,
            )

        fetch_t0 = time.perf_counter()
        all_bytes: list[bytes] = []
        from app.security.url_fetch import safe_fetch_image_bytes

        for img_url in img_urls:
            all_bytes.append(await safe_fetch_image_bytes(img_url, timeout=FETCH_TIMEOUT))

        cdn_fetch_ms = int(round((time.perf_counter() - fetch_t0) * 1000)) if latency_trace_enabled() else None
        if latency_trace_enabled() and cdn_fetch_ms is not None:
            log_event(
                "T3_cdn_fetch",
                job_id=request.job_id,
                fal_request_id=str(subscribe_req_id) if subscribe_req_id else None,
                fal_cdn_fetch_ms=cdn_fetch_ms,
            )

        cost = model_def.cost_per_call if model_def and model_def.cost_per_call else (spec.cost_per_call if spec else 0.1)
        latency_meta = {
            "T2_fal_api_ms": fal_http_ms,
            "T2_fal_mode": fal_mode,
            "fal_image_prep_ms": image_prep_ms,
            "fal_build_args_ms": build_args_ms,
        }
        if cdn_fetch_ms is not None:
            latency_meta["fal_cdn_fetch_ms"] = cdn_fetch_ms
        meta_out: dict[str, Any] = {
            "fal_result_keys": list(parse_payload.keys()) if isinstance(parse_payload, dict) else [],
            "all_image_urls": img_urls,
            "all_image_bytes": all_bytes[1:] if len(all_bytes) > 1 else [],
            "family": spec.family if spec else None,
            "latencyTrace": latency_meta,
            "metrics": parse_payload.get("metrics") if isinstance(parse_payload, dict) else None,
        }
        if subscribe_req_id:
            meta_out["fal_request_id"] = subscribe_req_id
        if inference_s is not None:
            meta_out["fal_inference_time"] = inference_s
        return GenerationResult(
            image_bytes=all_bytes[0] if all_bytes else None,
            provider=self.name,
            model=endpoint,
            cost=cost or 0.1,
            usage={
                "endpoint": endpoint,
                "arguments_keys": list(arguments.keys()),
                "image_count": len(all_bytes),
                "request_id": subscribe_req_id,
            },
            metadata=meta_out,
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
