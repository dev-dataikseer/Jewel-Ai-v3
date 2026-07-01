import os
from typing import Any

from sqlalchemy.orm import Session

from app.auth.security import decrypt_secret
from app.config import get_settings
from app.models import ModelDefinition, Provider
from app.providers.adapters.fal import FalAdapter

settings = get_settings()

ADAPTER_MAP = {
    "FAL": FalAdapter,
}

LEGACY_PROVIDERS = ("GEMINI", "IMAGEN", "OPENAI", "REPLICATE", "STABILITY", "COMFYUI", "A1111")


def _resolve_api_key(provider: Provider) -> str | None:
    if provider.encrypted_api_key:
        key = decrypt_secret(provider.encrypted_api_key)
        if key:
            return key
    if provider.env_key_name:
        env_val = os.environ.get(provider.env_key_name)
        if env_val:
            return env_val
        attr = provider.env_key_name.lower()
        return getattr(settings, attr, None)
    return settings.fal_key or None


def build_adapter(provider: Provider) -> FalAdapter:
    api_key = _resolve_api_key(provider)
    cls = ADAPTER_MAP.get(provider.name)
    if not cls:
        raise ValueError(f"Unknown provider: {provider.name}")
    if not api_key:
        raise ValueError("No API key for FAL — set FAL_KEY in environment or admin settings")
    return cls(api_key=api_key, model_name=provider.model_name)


def get_active_providers(db: Session) -> list[Provider]:
    return (
        db.query(Provider)
        .filter(Provider.is_active == True, Provider.name.in_(ADAPTER_MAP.keys()))  # noqa: E712
        .order_by(Provider.priority.asc())
        .all()
    )


def get_model_definition(db: Session, endpoint_id: str) -> ModelDefinition | None:
    return db.query(ModelDefinition).filter(ModelDefinition.endpoint_id == endpoint_id).first()


def resolve_default_endpoint(db: Session, workflow: str, has_input: bool = True) -> str | None:
    from seeds.fal_models_data import WORKFLOW_DEFAULTS

    preferred = WORKFLOW_DEFAULTS.get(workflow)
    if preferred:
        m = get_model_definition(db, preferred)
        if m and m.is_active:
            return preferred

    q = db.query(ModelDefinition).filter(ModelDefinition.is_active == True)  # noqa: E712
    m = q.order_by(ModelDefinition.sort_order.asc()).first()
    return m.endpoint_id if m else None


VTON_WORKFLOWS = frozenset({"JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"})


def filter_models_for_request(
    db: Session,
    workflow: str | None = None,
    has_input: bool = False,
    image_count: int = 0,
    active_only: bool = True,
    image_edit_only: bool = True,
) -> list[ModelDefinition]:
    """Return catalog models filtered by workflow, input availability, and image count."""
    q = db.query(ModelDefinition)
    if active_only:
        q = q.filter(ModelDefinition.is_active == True)  # noqa: E712

    models = q.order_by(ModelDefinition.sort_order.asc()).all()
    count = image_count if image_count > 0 else (1 if has_input else 0)

    result: list[ModelDefinition] = []
    for m in models:
        caps = m.capabilities or {}
        config = m.config or {}

        if image_edit_only:
            if not caps.get("image_to_image"):
                continue
            if caps.get("requires_mask"):
                continue

        if workflow and m.workflow_allowlist is not None and workflow not in m.workflow_allowlist:
            continue
        if workflow in VTON_WORKFLOWS:
            if not caps.get("virtual_try_on"):
                continue
        elif caps.get("virtual_try_on"):
            continue

        requires_image = caps.get("requires_image", True)
        min_images = int(config.get("min_images", 1 if requires_image else 0))

        if not has_input and requires_image:
            continue
        if has_input and requires_image and count < min_images:
            continue
        if caps.get("virtual_try_on") and count < 2:
            continue

        result.append(m)
    return result


def seed_providers(db: Session) -> None:
    for name in LEGACY_PROVIDERS:
        legacy = db.query(Provider).filter(Provider.name == name).first()
        if legacy:
            legacy.is_active = False

    fal = db.query(Provider).filter(Provider.name == "FAL").first()
    default_endpoint = "fal-ai/flux-pro/kontext"
    if not fal:
        db.add(
            Provider(
                name="FAL",
                display_name="fal.ai",
                model_name=default_endpoint,
                priority=10,
                is_active=True,
                env_key_name="FAL_KEY",
                capabilities={
                    "text_to_image": False,
                    "image_to_image": True,
                    "person_generation": True,
                    "material_accuracy": True,
                },
            )
        )
    else:
        fal.is_active = True
        fal.display_name = "fal.ai"
        fal.env_key_name = "FAL_KEY"
        if not fal.model_name or "gemini" in fal.model_name.lower():
            fal.model_name = default_endpoint
    db.commit()


def seed_model_definitions(db: Session) -> None:
    from seeds.fal_models_data import FAL_MODELS

    seed_ids = {spec["endpoint_id"] for spec in FAL_MODELS}
    for spec in FAL_MODELS:
        existing = db.query(ModelDefinition).filter(ModelDefinition.endpoint_id == spec["endpoint_id"]).first()
        if existing:
            existing.display_name = spec["display_name"]
            existing.category = spec["category"]
            existing.capabilities = spec["capabilities"]
            existing.input_schema = spec["input_schema"]
            existing.default_params = spec["default_params"]
            existing.workflow_allowlist = spec.get("workflow_allowlist")
            existing.config = spec.get("config", {})
            existing.sort_order = spec.get("sort_order", 100)
            existing.cost_per_call = spec.get("cost_per_call")
            existing.is_active = True
        else:
            db.add(
                ModelDefinition(
                    endpoint_id=spec["endpoint_id"],
                    display_name=spec["display_name"],
                    category=spec["category"],
                    capabilities=spec["capabilities"],
                    input_schema=spec["input_schema"],
                    default_params=spec["default_params"],
                    workflow_allowlist=spec.get("workflow_allowlist"),
                    config=spec.get("config", {}),
                    sort_order=spec.get("sort_order", 100),
                    cost_per_call=spec.get("cost_per_call"),
                    is_active=True,
                )
            )
    for stale in db.query(ModelDefinition).filter(~ModelDefinition.endpoint_id.in_(seed_ids)).all():
        stale.is_active = False
    db.commit()
