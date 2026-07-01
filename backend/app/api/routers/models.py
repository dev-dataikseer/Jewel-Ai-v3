from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import RequireAdmin, get_current_user
from app.database import get_db
from app.models import ModelDefinition, User
from app.providers.registry import filter_models_for_request, get_model_definition

router = APIRouter(prefix="/models", tags=["models"])

SYSTEM_FIELDS = {"prompt", "image_url", "image_urls", "negative_prompt"}


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
