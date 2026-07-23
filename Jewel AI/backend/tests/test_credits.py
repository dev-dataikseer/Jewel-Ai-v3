"""Credit debit concurrency / feature-flag tests."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.auth.security import hash_password
from app.database import Base
from app.models import User
from app.services.credits import debit_credits


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_debit_noop_when_flag_off(db, monkeypatch):
    from app import config as cfg

    monkeypatch.setattr(cfg.get_settings(), "enforce_user_credits", False)
    user = User(email="c@test.com", hashed_password=hash_password("x"), credits=5)
    db.add(user)
    db.commit()
    debit_credits(db, user.id, 3)
    db.refresh(user)
    assert user.credits == 5


def test_debit_enforced_and_insufficient(db, monkeypatch):
    from app import config as cfg

    monkeypatch.setattr(cfg.get_settings(), "enforce_user_credits", True)
    user = User(email="c2@test.com", hashed_password=hash_password("x"), credits=2)
    db.add(user)
    db.commit()
    debit_credits(db, user.id, 1, job_id=str(uuid.uuid4()))
    db.commit()
    db.refresh(user)
    assert user.credits == 1
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        debit_credits(db, user.id, 5)
    assert ei.value.status_code == 402


def test_refund_and_retry_debit_net_zero(db, monkeypatch):
    from app import config as cfg
    from app.services.credits import refund_credits

    monkeypatch.setattr(cfg.get_settings(), "enforce_user_credits", True)
    user = User(email="c3@test.com", hashed_password=hash_password("x"), credits=3)
    db.add(user)
    db.commit()
    job_id = str(uuid.uuid4())
    debit_credits(db, user.id, 1, job_id=job_id, description="job_create")
    db.commit()
    refund_credits(db, user.id, 1, job_id=job_id, description="job_enqueue_refund")
    db.commit()
    debit_credits(db, user.id, 1, job_id=job_id, description="job_retry")
    db.commit()
    db.refresh(user)
    assert user.credits == 2


def test_cancel_refund_when_no_fal_request(db, monkeypatch):
    from app import config as cfg
    from app.services.credits import refund_credits

    monkeypatch.setattr(cfg.get_settings(), "enforce_user_credits", True)
    user = User(email="c4@test.com", hashed_password=hash_password("x"), credits=1)
    db.add(user)
    db.commit()
    job_id = str(uuid.uuid4())
    debit_credits(db, user.id, 1, job_id=job_id, description="job_create")
    db.commit()
    refund_credits(db, user.id, 1, job_id=job_id, description="job_cancel_refund")
    db.commit()
    db.refresh(user)
    assert user.credits == 1
