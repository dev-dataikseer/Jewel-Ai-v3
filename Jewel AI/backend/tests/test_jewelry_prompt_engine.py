"""Engine selects V2 compose when Admin jewelry sections exist (no workflow profile required)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base
from app.models import PromptJewelrySection, PromptJewelrySectionVersion
from app.pipeline.composer import ComposeInput
from app.prompt_engine.attachments import ImageContext
from app.prompt_engine.engine import build_final_prompt


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


def test_jewelry_section_alone_reaches_final_prompt(db, monkeypatch):
    from app import config as cfg

    monkeypatch.setattr(cfg.get_settings(), "prompt_profile_v2", False)
    monkeypatch.setattr(cfg.get_settings(), "allow_prompt_file_fallback", True)

    section = PromptJewelrySection(
        id=str(uuid.uuid4()),
        workflow="CATALOG_IMAGE",
        jewelry_type="Ring",
        is_active=True,
    )
    db.add(section)
    db.flush()
    ver = PromptJewelrySectionVersion(
        id=str(uuid.uuid4()),
        section_id=section.id,
        version=1,
        content_json={"BODY": "UNIQUE_RING_SUBJECT_CLAUSE with claw setting physics."},
        is_active=True,
        source="test",
    )
    db.add(ver)
    db.flush()
    section.active_version_id = ver.id
    db.commit()

    final = build_final_prompt(
        db,
        ComposeInput(workflow="CATALOG_IMAGE", jewelry_type="Ring", prompt_text=None),
        image_ctx=ImageContext(has_product=True),
    )
    assert "UNIQUE_RING_SUBJECT_CLAUSE" in final.text
    assert final.debug.get("composePath") == "profile_v2"
    assert final.debug.get("jewelryVersionId") == ver.id


def test_empty_jewelry_section_does_not_force_v2(db, monkeypatch):
    from app import config as cfg

    monkeypatch.setattr(cfg.get_settings(), "prompt_profile_v2", False)
    monkeypatch.setattr(cfg.get_settings(), "allow_prompt_file_fallback", True)

    section = PromptJewelrySection(
        id=str(uuid.uuid4()),
        workflow="CATALOG_IMAGE",
        jewelry_type="Ring",
        is_active=True,
    )
    db.add(section)
    db.flush()
    ver = PromptJewelrySectionVersion(
        id=str(uuid.uuid4()),
        section_id=section.id,
        version=1,
        content_json={},
        is_active=True,
        source="test",
    )
    db.add(ver)
    db.flush()
    section.active_version_id = ver.id
    db.commit()

    from app.prompt_engine.profile_compose import should_use_profile_v2_compose

    assert should_use_profile_v2_compose(
        db, workflow="CATALOG_IMAGE", jewelry_type="Ring", has_reference=False
    ) is False
