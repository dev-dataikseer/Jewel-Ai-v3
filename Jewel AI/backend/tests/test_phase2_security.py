"""Phase 2 security: upload ownership exact-match and denylist fail-closed."""

from unittest.mock import MagicMock

import pytest

from app.auth import token_denylist
from app.auth.security import hash_password
from app.models import Asset, GenerationJob, User
from app.security.url_fetch import extract_upload_key, user_owns_upload_key


def _user(db, email: str, role: str = "user") -> User:
    user = User(email=email, hashed_password=hash_password("pass"), role=role, credits=100)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_extract_upload_key_strips_query_and_host():
    assert extract_upload_key("/uploads/foo.png") == "foo.png"
    assert extract_upload_key("https://host.example/uploads/foo.png?sig=abc&exp=1") == "foo.png"
    assert extract_upload_key("/uploads/dir/nested.png") == "dir/nested.png"
    assert extract_upload_key("https://evil.example/nope.png") is None


def test_ownership_exact_match_rejects_contains_planting(db_session):
    """Owning a path that *contains* another key must not grant access to that key."""
    owner = _user(db_session, "owner-idor@test.com")
    # Attacker-controlled name that contains the victim key as a substring.
    asset = Asset(
        user_id=owner.id,
        original_url="/uploads/attacker_victim.png",
        type="PRODUCT",
    )
    db_session.add(asset)
    db_session.commit()

    assert user_owns_upload_key(db_session, owner, "attacker_victim.png") is True
    # Classic contains IDOR: "victim.png" is a substring of "attacker_victim.png"
    assert user_owns_upload_key(db_session, owner, "victim.png") is False


def test_ownership_exact_match_on_job_and_logo_metadata(db_session):
    owner = _user(db_session, "owner-logo@test.com")
    other = _user(db_session, "other-logo@test.com")
    job = GenerationJob(
        user_id=owner.id,
        workflow="CATALOG_IMAGE",
        status="COMPLETED",
        input_url="/uploads/in.png",
        reference_url="https://api.example/uploads/ref.png?sig=1",
        model_url="/uploads/model.png",
        output_url="/uploads/out.png",
        provider_metadata={"logoUrl": "/uploads/logo.png"},
    )
    db_session.add(job)
    db_session.commit()

    assert user_owns_upload_key(db_session, owner, "ref.png") is True
    assert user_owns_upload_key(db_session, owner, "logo.png") is True
    assert user_owns_upload_key(db_session, other, "logo.png") is False
    assert user_owns_upload_key(db_session, other, "out.png") is False


def test_denylist_fail_closed_in_production(monkeypatch):
    token_denylist._LOCAL_DENY.clear()
    monkeypatch.setattr(
        token_denylist,
        "_redis_client",
        MagicMock(side_effect=ConnectionError("redis down")),
    )

    prod = MagicMock()
    prod.is_production = True
    monkeypatch.setattr(token_denylist, "get_settings", lambda: prod)
    assert token_denylist.is_refresh_jti_denied("jti-prod") is True

    dev = MagicMock()
    dev.is_production = False
    monkeypatch.setattr(token_denylist, "get_settings", lambda: dev)
    assert token_denylist.is_refresh_jti_denied("jti-dev") is False
    token_denylist._LOCAL_DENY.add("jti-local")
    assert token_denylist.is_refresh_jti_denied("jti-local") is True
    token_denylist._LOCAL_DENY.clear()


def test_share_link_expires_capped():
    from pydantic import ValidationError

    from app.schemas.common import ShareLinkCreate

    ok = ShareLinkCreate(job_id="x", expires_in_hours=168)
    assert ok.expires_in_hours == 168
    with pytest.raises(ValidationError):
        ShareLinkCreate(job_id="x", expires_in_hours=169)
    with pytest.raises(ValidationError):
        ShareLinkCreate(job_id="x", expires_in_hours=0)
