"""Tests for one-time TXT import."""

from sqlalchemy.orm import Session

from app.models import PromptMasterTemplate, PromptMasterVersion, PromptSubjectVersion
from seeds.prompt_txt_import import import_prompt_txt_library


def test_import_skips_when_already_seeded(db_session: Session):
    tmpl = PromptMasterTemplate(workflow="CATALOG_IMAGE", name="Catalog", is_active=True)
    db_session.add(tmpl)
    db_session.flush()
    db_session.add(
        PromptMasterVersion(
            template_id=tmpl.id,
            version=1,
            prompt_text="existing",
            layers=[],
            is_active=True,
            source="seed",
        )
    )
    db_session.commit()

    result = import_prompt_txt_library(db_session, force=False)
    assert result["imported"] is False
    assert result["reason"] == "already_seeded"


def test_import_force_populates_prompt_text(db_session: Session):
    result = import_prompt_txt_library(db_session, force=True)
    if result.get("reason") == "prompt library folder not found":
        return

    assert result["imported"] is True
    masters = db_session.query(PromptMasterVersion).all()
    assert masters
    assert any(m.prompt_text for m in masters)
    assert any(m.layers for m in masters)

    subjects = db_session.query(PromptSubjectVersion).all()
    if subjects:
        assert any(s.prompt_text for s in subjects)
