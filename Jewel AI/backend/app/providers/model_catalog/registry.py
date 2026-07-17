"""In-memory ModelSpec registry."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.providers.model_catalog.spec import ModelSpec, model_spec_from_seed_dict

_SPECS: dict[str, ModelSpec] | None = None


def _load_raw_seed_models() -> list[dict[str, Any]]:
    # Import enriched seed list (single source of schema/defaults during migration).
    from seeds.fal_models_data import FAL_MODELS

    return list(FAL_MODELS)


def load_registry(force: bool = False) -> dict[str, ModelSpec]:
    global _SPECS
    if _SPECS is not None and not force:
        return _SPECS
    specs = [model_spec_from_seed_dict(raw) for raw in _load_raw_seed_models()]
    # Optional T2I fallbacks registered in specs.t2i_fallbacks
    try:
        from app.providers.model_catalog.specs.t2i_fallbacks import T2I_FALLBACK_SPECS

        existing = {s.endpoint_id for s in specs}
        for extra in T2I_FALLBACK_SPECS:
            if extra.endpoint_id not in existing:
                specs.append(extra)
    except Exception:
        pass
    _SPECS = {s.endpoint_id: s for s in sorted(specs, key=lambda m: m.sort_order)}
    return _SPECS


def get_spec(endpoint_id: str) -> ModelSpec | None:
    return load_registry().get(endpoint_id)


def all_specs() -> list[ModelSpec]:
    return list(load_registry().values())


def seed_dicts() -> list[dict[str, Any]]:
    """Seed-compatible dicts including ui/limits enrichment from ModelSpec."""
    return [s.to_seed_dict() for s in all_specs()]


@lru_cache(maxsize=1)
def workflow_defaults() -> dict[str, str]:
    from seeds.fal_models_data import WORKFLOW_DEFAULTS

    return dict(WORKFLOW_DEFAULTS)
