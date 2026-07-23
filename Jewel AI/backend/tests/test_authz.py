"""Integration tests for authorization and tenancy."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.auth.security import create_access_token, create_webhook_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Asset, GenerationJob, User


@pytest.fixture()
def client(db_session):
    def _override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _user(db, email: str, role: str = "user") -> User:
    user = User(email=email, hashed_password=hash_password("pass"), role=role, credits=100)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _job(db, user: User, status: str = "COMPLETED") -> GenerationJob:
    job = GenerationJob(user_id=user.id, workflow="CATALOG_IMAGE", status=status, input_url="/uploads/x.jpg")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _asset(db, user: User) -> Asset:
    asset = Asset(user_id=user.id, original_url="/uploads/a.jpg", type="PRODUCT")
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def test_favorites_scoped_per_user(client, db_session):
    owner = _user(db_session, "owner@test.com")
    other = _user(db_session, "other@test.com")
    job = _job(db_session, owner)

    res = client.post(f"/api/favorites/{job.id}", headers=_auth(other))
    assert res.status_code == 404

    res = client.post(f"/api/favorites/{job.id}", headers=_auth(owner))
    assert res.status_code == 200

    favs = client.get("/api/favorites", headers=_auth(owner)).json()
    assert job.id in favs
    assert client.get("/api/favorites", headers=_auth(other)).json() == []


def test_share_link_requires_job_ownership(client, db_session):
    owner = _user(db_session, "owner2@test.com")
    other = _user(db_session, "other2@test.com")
    job = _job(db_session, owner)

    denied = client.post("/api/share-links", json={"job_id": job.id}, headers=_auth(other))
    assert denied.status_code == 404

    allowed = client.post("/api/share-links", json={"job_id": job.id}, headers=_auth(owner))
    assert allowed.status_code == 200
    body = allowed.json()
    assert "token" in body
    assert "id" in body

    listed = client.get("/api/share-links", headers=_auth(owner), params={"job_id": job.id})
    assert listed.status_code == 200
    assert any(item["id"] == body["id"] for item in listed.json()["items"])

    other_list = client.get("/api/share-links", headers=_auth(other))
    assert other_list.status_code == 200
    assert other_list.json()["items"] == []

    revoke_denied = client.delete(f"/api/share-links/{body['id']}", headers=_auth(other))
    assert revoke_denied.status_code == 404

    revoked = client.delete(f"/api/share-links/{body['id']}", headers=_auth(owner))
    assert revoked.status_code == 200
    assert client.get("/api/share-links", headers=_auth(owner), params={"job_id": job.id}).json()[
        "items"
    ] == []


def test_create_job_rejects_foreign_asset(client, db_session):
    owner = _user(db_session, "owner3@test.com")
    other = _user(db_session, "other3@test.com")
    asset = _asset(db_session, owner)

    res = client.post(
        "/api/jobs",
        json={"workflow": "CATALOG_IMAGE", "asset_id": asset.id, "jewelry_type": "Ring"},
        headers=_auth(other),
    )
    assert res.status_code == 400
    detail = str(res.json().get("detail", "")).lower()
    assert "asset" in detail or "belong" in detail or "required" in detail


def test_webhook_requires_valid_token(client, db_session):
    job = _job(db_session, _user(db_session, "wh@test.com"), status="PROCESSING")
    job.provider_metadata = {"fal_request_id": "req-abc"}
    db_session.commit()

    bad = client.post(f"/api/providers/fal/webhook/{job.id}?token=invalid", json={"status": "OK"})
    assert bad.status_code == 401

    token = create_webhook_token(job.id)
    ok = client.post(
        f"/api/providers/fal/webhook/{job.id}?token={token}",
        json={"status": "ERROR", "error": "test", "request_id": "req-abc"},
    )
    assert ok.status_code == 200


def test_webhook_rejects_request_id_mismatch(client, db_session):
    job = _job(db_session, _user(db_session, "wh2@test.com"), status="PROCESSING")
    job.provider_metadata = {"fal_request_id": "req-real"}
    db_session.commit()
    token = create_webhook_token(job.id)

    res = client.post(
        f"/api/providers/fal/webhook/{job.id}?token={token}",
        json={"status": "OK", "request_id": "req-attacker", "payload": {"images": []}},
    )
    assert res.status_code == 403
    db_session.refresh(job)
    assert job.status == "PROCESSING"
    assert not (job.provider_metadata or {}).get("webhook_accepted")


def test_webhook_idempotent_already_processed(client, db_session):
    job = _job(db_session, _user(db_session, "wh3@test.com"), status="PROCESSING")
    job.provider_metadata = {"fal_request_id": "req-idem", "webhook_completed": True}
    db_session.commit()
    token = create_webhook_token(job.id)

    res = client.post(
        f"/api/providers/fal/webhook/{job.id}?token={token}",
        json={"status": "OK", "request_id": "req-idem"},
    )
    assert res.status_code == 200
    assert res.json().get("status") == "already_processed"


def test_webhook_409_when_fal_request_id_missing(client, db_session):
    job = _job(db_session, _user(db_session, "wh4@test.com"), status="PROCESSING")
    job.provider_metadata = {}
    db_session.commit()
    token = create_webhook_token(job.id)
    res = client.post(
        f"/api/providers/fal/webhook/{job.id}?token={token}",
        json={"status": "OK", "request_id": "anything"},
    )
    assert res.status_code == 409


def test_bulk_job_rejects_over_50_assets():
    from pydantic import ValidationError

    from app.schemas.common import BulkJobCreate

    with pytest.raises(ValidationError):
        BulkJobCreate(asset_ids=[str(uuid.uuid4()) for _ in range(51)])


def test_production_rejects_sqlite(monkeypatch):
    from app.config import Settings, assert_production_settings, get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("NODE_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./jewel.db")
    monkeypatch.setenv("JWT_SECRET", "prod-secret-long-enough-value")
    monkeypatch.setenv("FAL_KEY", "fal-key")
    monkeypatch.setenv("FERNET_KEY", "x" * 44)
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-admin-pass")
    monkeypatch.setenv("DEFAULT_USER_PASSWORD", "strong-user-pass")
    monkeypatch.setenv("STORAGE_BACKEND", "r2")
    monkeypatch.setenv("API_PUBLIC_URL", "https://jewel.example.com")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://jewel.example.com")
    monkeypatch.setenv("SCHEMA_VIA_ALEMBIC", "true")
    monkeypatch.setenv("R2_BUCKET_NAME", "b")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "a")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "s")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://r2.example.com")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="PostgreSQL|DATABASE_URL|SQLite"):
        # Build settings from env via a fresh Settings instance path
        from app import config as cfg

        cfg.get_settings.cache_clear()
        # Patch the cached settings object fields directly for assert
        s = Settings(
            node_env="production",
            database_url="sqlite:///./jewel.db",
            jwt_secret="prod-secret-long-enough-value",
            fal_key="fal-key",
            fernet_key="x" * 44,
            admin_password="strong-admin-pass",
            default_user_password="strong-user-pass",
            storage_backend="r2",
            api_public_url="https://jewel.example.com",
            frontend_origin="https://jewel.example.com",
            schema_via_alembic=True,
            r2_bucket_name="b",
            r2_access_key_id="a",
            r2_secret_access_key="s",
            r2_endpoint_url="https://r2.example.com",
        )
        monkeypatch.setattr(cfg, "get_settings", lambda: s)
        assert_production_settings()
    get_settings.cache_clear()