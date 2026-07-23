import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    white_label_on: Mapped[bool] = mapped_column(Boolean, default=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="team")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    credits: Mapped[int] = mapped_column(Integer, default=100)
    role: Mapped[str] = mapped_column(String(32), default="user")
    team_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("teams.id"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    encrypted_totp_secret: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    totp_backup_hashes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    team: Mapped[Optional[Team]] = relationship(back_populates="users")
    jobs: Mapped[list["GenerationJob"]] = relationship(back_populates="user")
    assets: Mapped[list["Asset"]] = relationship(back_populates="user")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    before: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StylePreset(Base):
    __tablename__ = "style_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_addon: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PromptMasterTemplate(Base):
    __tablename__ = "prompt_master_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    active_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["PromptMasterVersion"]] = relationship(back_populates="template")


class PromptMasterVersion(Base):
    __tablename__ = "prompt_master_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_master_templates.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_role: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    camera_settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    environment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lighting_and_physics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preservation_lock: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    composition_mode: Mapped[str] = mapped_column(String(32), default="layered")
    layers: Mapped[Optional[dict | list]] = mapped_column(JSON, nullable=True)
    raw_override: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(32), default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    template: Mapped[PromptMasterTemplate] = relationship(back_populates="versions")


class PromptSubject(Base):
    __tablename__ = "prompt_subjects"
    __table_args__ = (UniqueConstraint("workflow", "jewelry_type", name="uq_subject_workflow_jewelry"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow: Mapped[str] = mapped_column(String(64), nullable=False, default="CATALOG_IMAGE", index=True)
    jewelry_type: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    active_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["PromptSubjectVersion"]] = relationship(back_populates="subject")


class PromptWorkflowLayerConfig(Base):
    __tablename__ = "prompt_workflow_layer_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    structural_layers: Mapped[list | dict] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PromptSubjectVersion(Base):
    __tablename__ = "prompt_subject_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_subjects.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    core_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anatomy_interaction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    physics_and_gravity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    placement_rules: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    composition_mode: Mapped[str] = mapped_column(String(32), default="layered")
    layers: Mapped[Optional[dict | list]] = mapped_column(JSON, nullable=True)
    raw_override: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(32), default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subject: Mapped[PromptSubject] = relationship(back_populates="versions")


class PromptVariant(Base):
    __tablename__ = "prompt_variants"
    __table_args__ = (UniqueConstraint("workflow", "variant_key", name="uq_variant_workflow_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    variant_key: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    active_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["PromptVariantVersion"]] = relationship(back_populates="variant")


class PromptVariantVersion(Base):
    __tablename__ = "prompt_variant_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    variant_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_variants.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    negative_addon: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    variant: Mapped[PromptVariant] = relationship(back_populates="versions")


class PromptFragment(Base):
    """Shared versioned prompt blocks (fidelity lock, execution modes, branding, attachments)."""

    __tablename__ = "prompt_fragments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    fragment_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    active_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["PromptFragmentVersion"]] = relationship(back_populates="fragment")


class PromptFragmentVersion(Base):
    __tablename__ = "prompt_fragment_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    fragment_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_fragments.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    # For ENVIRONMENT_POOL: JSON list of environment sentences (also mirrored in prompt_text as joined lines)
    content_json: Mapped[Optional[dict | list]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(32), default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fragment: Mapped[PromptFragment] = relationship(back_populates="versions")


# ── Prompt Profile V2 (JSON key→value sections, two pages per workflow) ──────


class PromptProfile(Base):
    """One workflow × reference_mode shell; active version holds content_json."""

    __tablename__ = "prompt_profiles"
    __table_args__ = (UniqueConstraint("workflow", "reference_mode", name="uq_profile_workflow_ref"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # without_reference | with_reference
    reference_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    active_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["PromptProfileVersion"]] = relationship(back_populates="profile")


class PromptProfileVersion(Base):
    __tablename__ = "prompt_profile_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_profiles.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Ordered section map: {"ROLE": "...", "CAMERA": "...", "NEGATIVE PROMPT": "..."}
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Optional environment pool for without_reference catalog (list of sentences)
    environment_pool: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(32), default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped[PromptProfile] = relationship(back_populates="versions")


class PromptJewelrySection(Base):
    """Jewelry-type sections (replaces prompt_subjects for V2)."""

    __tablename__ = "prompt_jewelry_sections"
    __table_args__ = (
        UniqueConstraint("workflow", "jewelry_type", name="uq_jewelry_section_workflow_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    jewelry_type: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    active_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["PromptJewelrySectionVersion"]] = relationship(back_populates="section")


class PromptJewelrySectionVersion(Base):
    __tablename__ = "prompt_jewelry_section_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("prompt_jewelry_sections.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(32), default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    section: Mapped[PromptJewelrySection] = relationship(back_populates="versions")


class PromptImageRole(Base):
    """Image-role instruction labels (replaces ATTACH_* fragments)."""

    __tablename__ = "prompt_image_roles"
    __table_args__ = (
        UniqueConstraint("role", "workflow", name="uq_image_role_workflow"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # product | theme | portrait | logo
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # NULL = global default; otherwise workflow override
    workflow: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Plain text; {index} substituted at compose time
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(32), default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_api_key: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    # Admin-scoped key for Platform Billing (GET /account/billing?expand=credits)
    encrypted_admin_api_key: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    env_key_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    base_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    health_status: Mapped[str] = mapped_column(String(32), default="unknown")
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ModelDefinition(Base):
    __tablename__ = "model_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    endpoint_id: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), default="FAL")
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    input_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    default_params: Mapped[dict] = mapped_column(JSON, default=dict)
    workflow_allowlist: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    cost_per_call: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProviderHealthLog(Base):
    __tablename__ = "provider_health_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    workflow: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    jewelry_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    preset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("style_presets.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    workflow: Mapped[str] = mapped_column(String(64), nullable=False)
    jewelry_type: Mapped[str] = mapped_column(String(255), nullable=False)
    preset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("style_presets.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    total_jobs: Mapped[int] = mapped_column(Integer, default=0)
    completed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    cost_policy: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    original_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    processed_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[Optional[User]] = relationship(back_populates="assets")


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        Index("ix_generation_jobs_status", "status"),
        Index("ix_jobs_user_id", "user_id"),
        Index("ix_jobs_user_created", "user_id", "created_at"),
        Index("ix_jobs_user_status", "user_id", "status"),
        Index("ix_jobs_batch_id", "batch_id"),
        Index("ix_jobs_celery_task_id", "celery_task_id"),
        Index("ix_jobs_status_processing_started", "status", "processing_started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    batch_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("batches.id", ondelete="CASCADE"), nullable=True
    )
    asset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("assets.id"), nullable=True)
    style_preset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("style_presets.id"), nullable=True)

    workflow: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    prompt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jewelry_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metal_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gemstone_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gemstone_cut: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gemstone_target_color: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    setting_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    background_style: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    lighting_style: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    input_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    reference_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    model_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    output_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    output_urls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    provider_used: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    provider_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    credits_used: Mapped[int] = mapped_column(Integer, default=0)

    master_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    subject_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    variant_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped[Optional[User]] = relationship(back_populates="jobs")
    favorite: Mapped[Optional["Favorite"]] = relationship(back_populates="job", uselist=False)
    share_links: Mapped[list["ShareLink"]] = relationship(back_populates="job")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_favorite_user_job"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[GenerationJob] = relationship(back_populates="favorite")


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, default=_uuid)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[GenerationJob] = relationship(back_populates="share_links")


class RateEntry(Base):
    __tablename__ = "rate_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metal_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    diamond_shape: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    diamond_color: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    diamond_clarity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    carat: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="PKR")
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
