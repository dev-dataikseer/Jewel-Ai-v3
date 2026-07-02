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
from app.models import Asset, Favorite, GenerationJob, User


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
    assert "token" in allowed.json()


def test_create_job_rejects_foreign_asset(client, db_session):
    owner = _user(db_session, "owner3@test.com")
    other = _user(db_session, "other3@test.com")
    asset = _asset(db_session, owner)

    res = client.post(
        "/api/jobs",
        json={"workflow": "CATALOG_IMAGE", "asset_id": asset.id, "jewelry_type": "Ring"},
        headers=_auth(other),
    )
    assert res.status_code == 404


def test_webhook_requires_valid_token(client, db_session):
    job = _job(db_session, _user(db_session, "wh@test.com"), status="PROCESSING")
    bad = client.post(f"/api/providers/fal/webhook/{job.id}?token=invalid", json={"status": "OK"})
    assert bad.status_code == 401

    token = create_webhook_token(job.id)
    ok = client.post(
        f"/api/providers/fal/webhook/{job.id}?token={token}",
        json={"status": "ERROR", "error": "test"},
    )
    assert ok.status_code == 200
