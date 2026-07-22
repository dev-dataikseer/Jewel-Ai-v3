from functools import lru_cache
import os
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    port: int = 8000
    node_env: str = "development"
    frontend_origin: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = "postgresql://jewel:jewel@localhost:5432/jewel_ai"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_worker_concurrency: int = 3

    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    fernet_key: str = ""

    admin_email: str = "admin@jewelai.com"
    admin_password: str = "changeme"
    default_user_email: str = "studio@jewelai.com"
    default_user_password: str = "studio123"
    force_seed_passwords: bool = False
    allow_prompt_reseed: bool | None = None
    # When true in production, compose may fall back to DEFAULT_FRAGMENTS / .txt files.
    # Default false in production — Admin DB is the sole runtime source.
    allow_prompt_file_fallback: bool = False
    webhook_pending_timeout_minutes: int = 20
    stuck_job_minutes: int = 15
    # Celery token-bucket for process_image_job (protects DB/R2; fal queue absorbs bursts).
    fal_celery_rate_limit: str = "10/s"
    # Temporary perf diagnostics — grep logs for LATENCY_TRACE
    latency_trace: bool = False
    # Prompt Profile V2: JSON key→value profiles (two pages: with/without reference).
    # When true, build_final_prompt uses profile_compose instead of fragments/layers.
    prompt_profile_v2: bool = False
    daily_job_limit: int = 100
    schema_via_alembic: bool = False
    # When true, debit user credits atomically on job create (SELECT FOR UPDATE).
    enforce_user_credits: bool = False
    sentry_dsn: str = ""
    csrf_cookie_name: str = "jewel_csrf"
    refresh_cookie_name: str = "jewel_refresh_token"

    fal_key: str = ""
    # Admin-scoped key required for Platform Billing APIs (credits). Falls back to fal_key.
    fal_admin_key: str = ""
    # When true, use fal queue webhooks (requires healthy Celery finalize). Default false =
    # subscribe/wait in-process (more reliable for Studio UX).
    fal_use_webhooks: bool = False
    # When true, always paste logo under the output instead of sending it as a fal reference.
    logo_force_compose: bool = False
    # Allow in-process job threads when Celery is down (dev). Production defaults false via property.
    allow_inline_jobs: bool | None = None
    # Recent catalog environments to avoid repeating for the same user (Modern Dynamic Catalog).
    env_rotation_lookback: int = 5
    api_public_url: str = "http://localhost:8000"
    # fal.ai billing / credits monitoring
    fal_credits_low_threshold: float = 5.0
    fal_billing_refresh_minutes: int = 7
    fal_billing_cache_ttl_seconds: int = 900
    media_signed_url_ttl_seconds: int = 7200

    storage_backend: str = "local"
    uploads_dir: str = "uploads"

    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_endpoint_url: str = ""
    r2_public_url: str = ""

    # Unused vendor stubs kept for env compatibility — fal.ai is the only adapter
    comfyui_base_url: str = "http://localhost:8188"
    a1111_base_url: str = "http://localhost:7860"
    openai_api_key: str = ""
    replicate_api_token: str = ""
    stability_api_key: str = ""

    @property
    def effective_allow_prompt_reseed(self) -> bool:
        if self.allow_prompt_reseed is not None:
            return self.allow_prompt_reseed
        return self.node_env == "development"

    @model_validator(mode="after")
    def apply_platform_urls(self) -> "Settings":
        """Use Railway public domain when localhost placeholders are still set."""
        # Railway Bucket credentials (map AWS_* → R2_* used by storage layer)
        if not self.r2_endpoint_url and os.environ.get("AWS_ENDPOINT_URL"):
            self.r2_endpoint_url = os.environ["AWS_ENDPOINT_URL"]
        if not self.r2_access_key_id and os.environ.get("AWS_ACCESS_KEY_ID"):
            self.r2_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
        if not self.r2_secret_access_key and os.environ.get("AWS_SECRET_ACCESS_KEY"):
            self.r2_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]
        if not self.r2_bucket_name and os.environ.get("AWS_S3_BUCKET_NAME"):
            self.r2_bucket_name = os.environ["AWS_S3_BUCKET_NAME"]

        domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("RAILWAY_STATIC_URL", "").replace("https://", "")
        if domain:
            if "localhost" in self.api_public_url or "127.0.0.1" in self.api_public_url:
                self.api_public_url = f"https://{domain}"
            if "localhost" in self.frontend_origin:
                self.frontend_origin = f"https://{domain}"
        return self

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.node_env == "production"

    @property
    def effective_allow_inline_jobs(self) -> bool:
        if self.allow_inline_jobs is not None:
            return self.allow_inline_jobs
        return not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_production_settings() -> list[str]:
    """Return warnings for insecure or incomplete production configuration."""
    s = get_settings()
    warnings: list[str] = []
    if not s.is_production:
        return warnings
    if s.jwt_secret in ("dev-secret-change-in-production", "", "changeme"):
        warnings.append("JWT_SECRET must be set to a strong random value in production")
    if not s.fal_key:
        warnings.append("FAL_KEY is required for image generation in production")
    if not s.fernet_key:
        warnings.append("FERNET_KEY should be set to encrypt provider API keys at rest")
    if "localhost" in s.api_public_url:
        warnings.append("API_PUBLIC_URL should be a public HTTPS URL for fal webhooks")
    if s.admin_password in ("changeme", "admin", "password", "123456"):
        warnings.append("ADMIN_PASSWORD must not use a default/weak value in production")
    if s.default_user_password in ("studio123", "changeme", "password", "123456"):
        warnings.append("DEFAULT_USER_PASSWORD must not use a default/weak value in production")
    if s.storage_backend == "local":
        warnings.append("STORAGE_BACKEND=local is ephemeral on most hosts; use r2/s3/object in production")
    elif s.storage_backend in ("r2", "s3", "object"):
        if not (s.r2_bucket_name and s.r2_access_key_id and s.r2_secret_access_key and s.r2_endpoint_url):
            warnings.append("Object storage selected but R2/AWS bucket credentials are incomplete")
    return warnings


def assert_production_settings() -> None:
    """Fail fast on critical misconfiguration in production."""
    s = get_settings()
    issues = validate_production_settings()
    critical_markers = (
        "JWT_SECRET",
        "API_PUBLIC_URL",
        "ADMIN_PASSWORD",
        "DEFAULT_USER_PASSWORD",
        "FAL_KEY",
        "FERNET_KEY",
        "STORAGE_BACKEND=local",
        "bucket credentials",
        "DATABASE_URL",
        "SCHEMA_VIA_ALEMBIC",
        "FRONTEND_ORIGIN",
    )
    # SQLite cannot handle concurrent API + Celery + Beat writers.
    db_url = (s.database_url or "").lower()
    if "sqlite" in db_url:
        issues.append("DATABASE_URL must use PostgreSQL in production (SQLite is local/dev only)")
    if not s.schema_via_alembic:
        issues.append("SCHEMA_VIA_ALEMBIC must be true in production")
    # Same-site cookie auth requires SPA and API on the same registrable host.
    try:
        from urllib.parse import urlparse

        api_host = urlparse(s.api_public_url).hostname or ""
        fe_hosts = {urlparse(o).hostname or "" for o in s.cors_origins}
        if api_host and fe_hosts and api_host not in fe_hosts:
            issues.append(
                "FRONTEND_ORIGIN host must match API_PUBLIC_URL host in production (same-site cookies)"
            )
    except Exception:
        pass
    critical = [w for w in issues if any(m in w for m in critical_markers)]
    if critical:
        raise RuntimeError("Production configuration invalid: " + "; ".join(critical))
