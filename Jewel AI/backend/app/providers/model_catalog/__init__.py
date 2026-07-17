"""Model-first fal catalog: specs, builders, preprocess, validation."""

from app.providers.model_catalog.builders import build_arguments, get_builder
from app.providers.model_catalog.preprocess import prepare_images
from app.providers.model_catalog.registry import all_specs, get_spec, load_registry, seed_dicts
from app.providers.model_catalog.spec import SYSTEM_FIELDS, ImageContract, ModelSpec

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
