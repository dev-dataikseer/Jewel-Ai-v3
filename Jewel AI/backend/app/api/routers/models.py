from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import RequireAdmin, get_current_user
from app.database import get_db
from app.models import ModelDefinition, User
from app.providers.model_catalog.registry import get_spec
from app.providers.model_catalog.spec import SYSTEM_FIELDS
from app.providers.registry import filter_models_for_request, get_model_definition

router = APIRouter(prefix="/models", tags=["models"])


class ModelLimitsOut(BaseModel):
    min_images: int = 1
    max_images: int = 14
    max_prompt_chars: Optional[int] = None  # effective packing budget
    recommended_max_prompt_chars: Optional[int] = None
    official_max_prompt_chars: Optional[int] = None
    official_prompt_status: Optional[str] = None
    official_prompt_note: Optional[str] = None


class ModelUiOut(BaseModel):
    provider: str = "fal"
    provider_label: str = "fal.ai"
    tasks: list[str] = Field(default_factory=list)
    docs_url: Optional[str] = None
    pricing_note: Optional[str] = None
    supports_edit: bool = True
    supports_i2i: bool = True
    supports_t2i: bool = False
    badge: Optional[str] = None
    max_images: int = 14
    min_images: int = 1
    max_prompt_chars: Optional[int] = None
    recommended_max_prompt_chars: Optional[int] = None
    official_max_prompt_chars: Optional[int] = None
    official_prompt_status: Optional[str] = None


class ModelOut(BaseModel):
    endpoint_id: str
    display_name: str
    provider: str
    category: str
    capabilities: dict[str, Any] = Field(default_factory=dict)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    default_params: dict[str, Any] = Field(default_factory=dict)
    workflow_allowlist: Optional[list[str]] = None
    is_active: bool = True
    sort_order: int = 100
    cost_per_call: Optional[float] = None
    model_info: Optional[dict[str, Any]] = None
    ui: Optional[ModelUiOut] = None
    limits: Optional[ModelLimitsOut] = None
    family: Optional[str] = None

    model_config = {"from_attributes": True}


class ModelUpdate(BaseModel):
    is_active: Optional[bool] = None
    default_params: Optional[dict[str, Any]] = None
    display_name: Optional[str] = None
    sort_order: Optional[int] = None


def _model_out(m: ModelDefinition) -> ModelOut:
    schema = dict(m.input_schema or {})
    props = dict(schema.get("properties") or {})
    for field in SYSTEM_FIELDS:
        props.pop(field, None)
    schema["properties"] = props

    cfg = m.config or {}
    ui_raw = cfg.get("ui") or {}
    limits_raw = cfg.get("limits") or {}
    spec = get_spec(m.endpoint_id)

    if spec and not ui_raw:
        ui_raw = spec.to_seed_dict()["config"].get("ui") or {}
        limits_raw = spec.to_seed_dict()["config"].get("limits") or {}

    ui = None
    if ui_raw:
        ui = ModelUiOut(
            provider=str(ui_raw.get("provider") or "fal"),
            provider_label=str(ui_raw.get("provider_label") or "fal.ai"),
            tasks=list(ui_raw.get("tasks") or []),
            docs_url=ui_raw.get("docs_url"),
            pricing_note=ui_raw.get("pricing_note"),
            supports_edit=bool(ui_raw.get("supports_edit", True)),
            supports_i2i=bool(ui_raw.get("supports_i2i", True)),
            supports_t2i=bool(ui_raw.get("supports_t2i", False)),
            badge=ui_raw.get("badge"),
            max_images=int(ui_raw.get("max_images") or limits_raw.get("max_images") or 14),
            min_images=int(ui_raw.get("min_images") or limits_raw.get("min_images") or 1),
            max_prompt_chars=ui_raw.get("max_prompt_chars") or limits_raw.get("max_prompt_chars"),
            recommended_max_prompt_chars=ui_raw.get("recommended_max_prompt_chars")
            or limits_raw.get("recommended_max_prompt_chars"),
            official_max_prompt_chars=ui_raw.get("official_max_prompt_chars")
            or limits_raw.get("official_max_prompt_chars"),
            official_prompt_status=ui_raw.get("official_prompt_status")
            or limits_raw.get("official_prompt_status"),
        )

    limits = None
    if limits_raw or ui:
        limits = ModelLimitsOut(
            min_images=int(limits_raw.get("min_images") or (ui.min_images if ui else 1)),
            max_images=int(limits_raw.get("max_images") or (ui.max_images if ui else 14)),
            max_prompt_chars=limits_raw.get("max_prompt_chars") or (ui.max_prompt_chars if ui else None),
            recommended_max_prompt_chars=limits_raw.get("recommended_max_prompt_chars")
            or (ui.recommended_max_prompt_chars if ui else None),
            official_max_prompt_chars=limits_raw.get("official_max_prompt_chars")
            or (ui.official_max_prompt_chars if ui else None),
            official_prompt_status=limits_raw.get("official_prompt_status")
            or (ui.official_prompt_status if ui else None),
            official_prompt_note=limits_raw.get("official_prompt_note") or cfg.get("official_prompt_note"),
        )

    # Prefer live ModelSpec enrichment when available
    if spec is not None:
        packing = spec.image.effective_packing_chars()
        if limits:
            limits = limits.model_copy(
                update={
                    "max_prompt_chars": packing,
                    "recommended_max_prompt_chars": spec.image.recommended_max_prompt_chars
                    or spec.image.max_prompt_chars
                    or limits.recommended_max_prompt_chars,
                    "official_max_prompt_chars": spec.image.official_max_prompt_chars,
                    "official_prompt_status": spec.image.official_prompt_status,
                    "official_prompt_note": spec.image.official_prompt_note,
                }
            )
        if ui:
            ui = ui.model_copy(
                update={
                    "max_prompt_chars": packing,
                    "recommended_max_prompt_chars": limits.recommended_max_prompt_chars if limits else None,
                    "official_max_prompt_chars": spec.image.official_max_prompt_chars,
                    "official_prompt_status": spec.image.official_prompt_status,
                }
            )

    return ModelOut(
        endpoint_id=m.endpoint_id,
        display_name=m.display_name,
        provider=m.provider,
        category=m.category,
        capabilities=m.capabilities or {},
        input_schema=schema,
        default_params=m.default_params or {},
        workflow_allowlist=m.workflow_allowlist,
        is_active=m.is_active,
        sort_order=m.sort_order,
        cost_per_call=m.cost_per_call,
        model_info=cfg.get("model_info"),
        ui=ui,
        limits=limits,
        family=cfg.get("family") or (spec.family if spec else None),
    )


@router.get("", response_model=list[ModelOut])
def list_models(
    workflow: Optional[str] = None,
    has_input: bool = False,
    image_count: int = 0,
    image_edit_only: bool = True,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    models = filter_models_for_request(
        db,
        workflow=workflow,
        has_input=has_input,
        image_count=image_count,
        active_only=True,
        image_edit_only=image_edit_only,
    )
    return [_model_out(m) for m in models]


@router.get("/admin", response_model=list[ModelOut])
def list_models_admin(user: RequireAdmin, db: Session = Depends(get_db)):
    models = db.query(ModelDefinition).order_by(ModelDefinition.sort_order.asc()).all()
    return [_model_out(m) for m in models]


@router.get("/{endpoint_id:path}", response_model=ModelOut)
def get_model(endpoint_id: str, db: Session = Depends(get_db)):
    m = get_model_definition(db, endpoint_id)
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    return _model_out(m)


@router.patch("/{endpoint_id:path}", response_model=ModelOut)
def update_model(endpoint_id: str, body: ModelUpdate, user: RequireAdmin, db: Session = Depends(get_db)):
    m = get_model_definition(db, endpoint_id)
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    if body.is_active is not None:
        m.is_active = body.is_active
    if body.default_params is not None:
        m.default_params = body.default_params
    if body.display_name is not None:
        m.display_name = body.display_name
    if body.sort_order is not None:
        m.sort_order = body.sort_order
    db.commit()
    db.refresh(m)
    return _model_out(m)
