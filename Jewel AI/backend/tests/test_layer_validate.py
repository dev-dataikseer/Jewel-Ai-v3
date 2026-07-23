"""Layer validation for Admin prompt saves."""

from pathlib import Path

from app.pipeline.layer_derive import derive_layers_from_raw_text
from app.pipeline.layer_validate import validate_master_layers, validate_subject_layers


import pytest

def test_catalog_master_with_engine_placeholders_passes_validation():
    root = Path(__file__).resolve().parents[2] / "docs" / "Modals" / "Prompts"
    file_path = root / "CATALOG_IMAGE_master.txt"
    if not file_path.exists():
        pytest.skip("Prompt doc file not found")
    text = file_path.read_text(encoding="utf-8")
    layers = derive_layers_from_raw_text(text, "CATALOG_IMAGE", scope="master")
    validate_master_layers(layers)


def test_custom_prompt_master_with_placeholders_passes_validation():
    root = Path(__file__).resolve().parents[2] / "docs" / "Modals" / "Prompts"
    file_path = root / "CUSTOM_PROMPT_master.txt"
    if not file_path.exists():
        pytest.skip("Prompt doc file not found")
    text = file_path.read_text(encoding="utf-8")
    layers = derive_layers_from_raw_text(text, "CUSTOM_PROMPT", scope="master")
    validate_master_layers(layers)


def test_subject_ring_text_passes_validation():
    root = Path(__file__).resolve().parents[2] / "docs" / "Modals" / "Prompts"
    file_path = root / "ring.txt"
    if not file_path.exists():
        pytest.skip("Prompt doc file not found")
    text = file_path.read_text(encoding="utf-8")
    layers = derive_layers_from_raw_text(text, "CATALOG_IMAGE", scope="subject")
    validate_subject_layers(layers)
