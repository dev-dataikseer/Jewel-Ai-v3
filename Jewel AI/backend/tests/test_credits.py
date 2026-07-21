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
