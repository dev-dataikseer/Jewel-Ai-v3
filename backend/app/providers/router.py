from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Provider, ProviderHealthLog
from app.providers import circuit_breaker
from app.providers.registry import (
    build_adapter,
    get_active_providers,
    get_model_definition,
    resolve_default_endpoint,
)
from app.providers.types import GenerationRequest, GenerationResult

logger = get_logger(__name__)


def _model_supports_request(model_def, request: GenerationRequest) -> bool:
    if not model_def:
        return True
    caps = model_def.capabilities or {}
    has_images = bool(request.image_urls)
    if caps.get("requires_image", True) and not has_images:
        return False
    if caps.get("virtual_try_on") and len(request.image_urls) < 2:
        return False
    if has_images and not caps.get("image_to_image", False):
        return False
    if request.workflow in ("JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON") and not caps.get("person_generation", False):
        return False
    if request.workflow == "GEMSTONE_COLOR_CHANGE" and not caps.get("material_accuracy", False):
        return False
    return True


def provider_supports_request(provider: Provider, request: GenerationRequest) -> bool:
    caps = provider.capabilities or {}
    has_images = bool(request.image_urls)
    if not has_images:
        return False
    if not caps.get("image_to_image", False):
        return False
    if request.workflow in ("JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON") and not caps.get("person_generation", False):
        return False
    if request.workflow == "GEMSTONE_COLOR_CHANGE" and not caps.get("material_accuracy", False):
        return False
    return True


async def route_generation(db: Session, request: GenerationRequest) -> tuple[GenerationResult, list[str]]:
    chain: list[str] = []
    providers = get_active_providers(db)
    last_error: Exception | None = None

    has_input = bool(request.image_urls)
    endpoint = (
        request.model_endpoint_id
        or request.model_override
        or resolve_default_endpoint(db, request.workflow, has_input)
    )
    model_def = get_model_definition(db, endpoint) if endpoint else None

    if model_def and not _model_supports_request(model_def, request):
        fallback = resolve_default_endpoint(db, request.workflow, has_input)
        if fallback and fallback != endpoint:
            endpoint = fallback
            model_def = get_model_definition(db, endpoint)
            request.model_endpoint_id = endpoint
        elif not _model_supports_request(model_def, request):
            raise ValueError(f"Model {endpoint} does not support this workflow/input combination")

    for prov in providers:
        chain.append(prov.name)
        if circuit_breaker.is_circuit_open(prov.name):
            logger.info("Skipping provider — circuit open", extra={"extra_fields": {"provider": prov.name}})
            continue
        if not provider_supports_request(prov, request):
            continue
        try:
            adapter = build_adapter(prov)
        except ValueError as e:
            logger.warning(str(e))
            continue

        try:
            if endpoint:
                request.model_endpoint_id = endpoint
            result = await adapter.generate(request, model_def=model_def, db=db)
            circuit_breaker.record_success(prov.name)
            prov.health_status = "healthy"
            db.add(ProviderHealthLog(provider_name=prov.name, status="healthy", message=endpoint or "ok"))
            db.commit()
            return result, chain
        except Exception as e:
            circuit_breaker.record_failure(prov.name)
            prov.health_status = "degraded"
            db.add(ProviderHealthLog(provider_name=prov.name, status="failed", message=str(e)[:500]))
            db.commit()
            logger.warning("Provider failed", extra={"extra_fields": {"provider": prov.name, "error": str(e)}})
            last_error = e
            continue

    raise RuntimeError(f"All providers failed. Chain: {chain}. Last error: {last_error}")


async def check_all_provider_health(db: Session) -> list[dict]:
    results = []
    for prov in db.query(Provider).filter(Provider.is_active == True).all():  # noqa: E712
        try:
            adapter = build_adapter(prov)
            status = await adapter.health_check()
            prov.health_status = "healthy" if status.healthy else "unhealthy"
            results.append({"name": prov.name, "healthy": status.healthy, "message": status.message})
        except Exception as e:
            prov.health_status = "unhealthy"
            results.append({"name": prov.name, "healthy": False, "message": str(e)})
    db.commit()
    return results
