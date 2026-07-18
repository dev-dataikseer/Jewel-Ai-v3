"""Model-first fal catalog: specs, builders, preprocess, validation."""

from __future__ import annotations

from typing import Any

__all__ = [
    "SYSTEM_FIELDS",
    "ImageContract",
    "ModelSpec",
    "all_specs",
    "build_arguments",
    "get_builder",
    "get_spec",
    "load_registry",
    "prepare_images",
    "seed_dicts",
]


def __getattr__(name: str) -> Any:
    if name in {"SYSTEM_FIELDS", "ImageContract", "ModelSpec"}:
        from app.providers.model_catalog import spec as _spec

        return getattr(_spec, name)
    if name in {"all_specs", "get_spec", "load_registry", "seed_dicts"}:
        from app.providers.model_catalog import registry as _registry

        return getattr(_registry, name)
    if name in {"build_arguments", "get_builder"}:
        from app.providers.model_catalog import builders as _builders

        return getattr(_builders, name)
    if name == "prepare_images":
        from app.providers.model_catalog.preprocess import prepare_images

        return prepare_images
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
