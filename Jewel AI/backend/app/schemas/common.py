from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional["UserOut"] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str]
    role: str
    credits: int
    team_id: Optional[str] = None

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    workflow: str = "CATALOG_IMAGE"
    asset_id: Optional[str] = None
    project_id: Optional[str] = None
    prompt_text: Optional[str] = None
    jewelry_type: Optional[str] = "Ring"
    metal_type: Optional[str] = None
    gemstone_type: Optional[str] = None
    gemstone_cut: Optional[str] = None
    gemstone_target_color: Optional[str] = None
    setting_type: Optional[str] = None
    background_style: Optional[str] = None
    lighting_style: Optional[str] = None
    style_preset_id: Optional[str] = None
    reference_url: Optional[str] = None
    model_url: Optional[str] = None
    logo_asset_id: Optional[str] = None
    logo_url: Optional[str] = None
    aspect_ratio: str = "1:1"
    person_generation: str = "ALLOW_ADULT"
    number_of_images: int = 1
    model_name: Optional[str] = None  # deprecated — use model_endpoint_id
    model_endpoint_id: Optional[str] = None
    model_params: dict[str, Any] = Field(default_factory=dict)


class BulkJobCreate(BaseModel):
    workflow: str = "CATALOG_IMAGE"
    asset_ids: list[str]
    jewelry_type: str = "Ring"
    batch_name: Optional[str] = None
    aspect_ratio: str = "1:1"
    person_generation: str = "ALLOW_ADULT"
    number_of_images: int = 1
    model_name: Optional[str] = None
    model_endpoint_id: Optional[str] = None
    model_params: dict[str, Any] = Field(default_factory=dict)
    style_preset_id: Optional[str] = None
    reference_url: Optional[str] = None
    model_url: Optional[str] = None
    logo_asset_id: Optional[str] = None
    logo_url: Optional[str] = None
    background_style: Optional[str] = None
    prompt_text: Optional[str] = None
    metal_type: Optional[str] = None
    lighting_style: Optional[str] = None
    gemstone_type: Optional[str] = None
    gemstone_cut: Optional[str] = None
    gemstone_target_color: Optional[str] = None
    setting_type: Optional[str] = None


class BatchOut(BaseModel):
    id: str
    name: Optional[str] = None
    workflow: str
    jewelry_type: str
    status: str
    total_jobs: int
    completed_jobs: int
    pending_jobs: int = 0
    processing_jobs: int = 0
    failed_jobs: int = 0
    cancelled_jobs: int = 0
    created_at: datetime
    updated_at: datetime
    jobs: list["JobOut"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: str
    workflow: str
    status: str
    prompt_text: Optional[str] = None
    final_prompt: Optional[str] = None
    jewelry_type: Optional[str] = None
    metal_type: Optional[str] = None
    gemstone_target_color: Optional[str] = None
    background_style: Optional[str] = None
    input_url: Optional[str] = None
    reference_url: Optional[str] = None
    model_url: Optional[str] = None
    output_url: Optional[str] = None
    output_urls: Optional[list[str]] = None
    asset_id: Optional[str] = None
    error_message: Optional[str] = None
    provider_used: Optional[str] = None
    provider_model: Optional[str] = None
    provider_metadata: Optional[dict[str, Any]] = None
    master_version_id: Optional[str] = None
    subject_version_id: Optional[str] = None
    variant_version_id: Optional[str] = None
    cost: Optional[float] = None
    credits_used: int = 0
    retry_count: int = 0
    processing_started_at: Optional[datetime] = None
    batch_id: Optional[str] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetOut(BaseModel):
    id: str
    original_url: str
    type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptTestRequest(BaseModel):
    workflow: str
    jewelry_type: Optional[str] = "Ring"
    prompt_text: Optional[str] = None
    metal_type: Optional[str] = None
    gemstone_target_color: Optional[str] = None
    background_style: Optional[str] = None
    lighting_style: Optional[str] = None
    style_preset_id: Optional[str] = None
    model_endpoint_id: Optional[str] = None
    model_params: dict[str, Any] = Field(default_factory=dict)
    image_url: Optional[str] = None


class PromptTestResponse(BaseModel):
    prompt: str
    negative_prompt: str
    debug: dict[str, Any]


class ProviderOut(BaseModel):
    id: str
    name: str
    display_name: str
    model_name: str
    priority: int
    is_active: bool
    health_status: str
    has_api_key: bool = False
    has_admin_api_key: bool = False
    capabilities: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class ProviderUpdate(BaseModel):
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    admin_api_key: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    base_url: Optional[str] = None


class RateEntryCreate(BaseModel):
    rate_type: str
    value: float
    metal_type: Optional[str] = None
    diamond_shape: Optional[str] = None
    diamond_color: Optional[str] = None
    diamond_clarity: Optional[str] = None
    carat: Optional[str] = None
    currency: str = "PKR"
    city: Optional[str] = None
    notes: Optional[str] = None


class ShareLinkCreate(BaseModel):
    job_id: str
    expires_in_hours: int = 72


TokenResponse.model_rebuild()
