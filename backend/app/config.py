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
    allow_prompt_reseed: bool | None = None

    @property
    def effective_allow_prompt_reseed(self) -> bool:
        if self.allow_prompt_reseed is not None:
            return self.allow_prompt_reseed
        return self.node_env == "development"

    fal_key: str = ""
    api_public_url: str = "http://localhost:8000"

    storage_backend: str = "local"
    uploads_dir: str = "uploads"

    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_endpoint_url: str = ""
    r2_public_url: str = ""

    comfyui_base_url: str = "http://localhost:8188"
    a1111_base_url: str = "http://localhost:7860"
    openai_api_key: str = ""
    replicate_api_token: str = ""
    stability_api_key: str = ""

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
    return warnings


def assert_production_settings() -> None:
    """Fail fast on critical misconfiguration in production."""
    issues = validate_production_settings()
    critical = [w for w in issues if "JWT_SECRET" in w or "API_PUBLIC_URL" in w]
    if critical:
        raise RuntimeError("Production configuration invalid: " + "; ".join(critical))
