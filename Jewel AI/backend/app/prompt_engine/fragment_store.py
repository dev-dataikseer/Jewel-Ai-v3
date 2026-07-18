"""Load versioned prompt fragments from DB with default fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.prompt_engine.fragment_defaults import (
    DEFAULT_ENVIRONMENT_POOL,
    DEFAULT_FRAGMENTS,
    ENVIRONMENT_POOL,
    FRAGMENT_LABELS,
    substitute,
)

logger = logging.getLogger(__name__)


def get_fragment_text(db: Session | None, key: str, variables: dict[str, Any] | None = None) -> str:
    """Return active fragment text for key, substituted; falls back to DEFAULT_FRAGMENTS."""
    raw = _load_raw(db, key)
    return substitute(raw, variables or {})


def get_fragment_meta(db: Session | None, key: str) -> dict[str, Any]:
    """Return text + version id for promptDebug."""
    if db is not None:
        try:
            from app.models import PromptFragment, PromptFragmentVersion

            frag = db.query(PromptFragment).filter(PromptFragment.fragment_key == key).first()
            if frag and frag.active_version_id:
                ver = (
                    db.query(PromptFragmentVersion)
                    .filter(PromptFragmentVersion.id == frag.active_version_id)
                    .first()
                )
                if ver and ver.prompt_text is not None:
                    return {
                        "key": key,
                        "text": ver.prompt_text,
                        "version_id": ver.id,
                        "version": ver.version,
                        "source": ver.source,
                    }
        except Exception as exc:
            logger.debug("fragment load failed for %s: %s", key, exc)
    return {
        "key": key,
        "text": DEFAULT_FRAGMENTS.get(key, ""),
        "version_id": None,
        "version": 0,
        "source": "default",
    }


def get_environment_pool(db: Session | None = None) -> list[str]:
    if db is not None:
        try:
            from app.models import PromptFragment, PromptFragmentVersion

            frag = db.query(PromptFragment).filter(PromptFragment.fragment_key == ENVIRONMENT_POOL).first()
            if frag and frag.active_version_id:
                ver = (
                    db.query(PromptFragmentVersion)
                    .filter(PromptFragmentVersion.id == frag.active_version_id)
                    .first()
                )
                if ver:
                    if isinstance(ver.content_json, list) and ver.content_json:
                        return [str(x) for x in ver.content_json if str(x).strip()]
                    if ver.prompt_text:
                        try:
                            parsed = json.loads(ver.prompt_text)
                            if isinstance(parsed, list) and parsed:
                                return [str(x) for x in parsed if str(x).strip()]
                        except json.JSONDecodeError:
                            lines = [ln.strip() for ln in ver.prompt_text.splitlines() if ln.strip()]
                            if lines:
                                return lines
        except Exception as exc:
            logger.debug("environment pool load failed: %s", exc)
    return list(DEFAULT_ENVIRONMENT_POOL)


def _load_raw(db: Session | None, key: str) -> str:
    meta = get_fragment_meta(db, key)
    return meta.get("text") or DEFAULT_FRAGMENTS.get(key, "")


def seed_prompt_fragments(db: Session, *, force: bool = False) -> int:
    """Upsert fragment shells with seed text. Returns number of fragments ensured."""
    from app.models import PromptFragment, PromptFragmentVersion

    count = 0
    for key, text in DEFAULT_FRAGMENTS.items():
        content_json = None
        prompt_text = text
        if key == ENVIRONMENT_POOL:
            content_json = list(DEFAULT_ENVIRONMENT_POOL)
            prompt_text = json.dumps(content_json, indent=2)

        frag = db.query(PromptFragment).filter(PromptFragment.fragment_key == key).first()
        if not frag:
            frag = PromptFragment(
                fragment_key=key,
                name=FRAGMENT_LABELS.get(key, key),
                is_active=True,
            )
            db.add(frag)
            db.flush()
            ver = PromptFragmentVersion(
                fragment_id=frag.id,
                version=1,
                prompt_text=prompt_text,
                content_json=content_json,
                is_active=True,
                source="seed",
            )
            db.add(ver)
            db.flush()
            frag.active_version_id = ver.id
            count += 1
        elif force or not frag.active_version_id:
            last = (
                db.query(PromptFragmentVersion)
                .filter(PromptFragmentVersion.fragment_id == frag.id)
                .order_by(PromptFragmentVersion.version.desc())
                .first()
            )
            version_num = (last.version + 1) if last else 1
            db.query(PromptFragmentVersion).filter(PromptFragmentVersion.fragment_id == frag.id).update(
                {"is_active": False}
            )
            ver = PromptFragmentVersion(
                fragment_id=frag.id,
                version=version_num,
                prompt_text=prompt_text,
                content_json=content_json,
                is_active=True,
                source="seed",
            )
            db.add(ver)
            db.flush()
            frag.active_version_id = ver.id
            count += 1
    db.commit()
    return count
