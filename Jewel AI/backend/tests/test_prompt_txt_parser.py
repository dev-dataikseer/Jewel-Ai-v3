"""Tests for data/seed-prompt-templates/*.txt parser."""

from pathlib import Path

from app.pipeline.layer_derive import parse_labeled_sections
from seeds.prompt_txt_parser import (
    FILE_WORKFLOW_MAP,
    load_all_prompt_files,
    master_raw_to_db_layers,
    resolve_prompts_directory,
)


def test_prompt_library_dir_found():
    assert resolve_prompts_directory() is not None


def test_all_nine_workflows_parse():
    workflows = load_all_prompt_files()
    assert len(workflows) == len(FILE_WORKFLOW_MAP)
    ids = {w.workflow for w in workflows}
    assert "CATALOG_IMAGE" in ids
    assert "BULK_GENERATION" in ids


def test_catalog_master_has_raw_text_and_layers():
    cat = next(w for w in load_all_prompt_files() if w.workflow == "CATALOG_IMAGE")
    assert cat.master_raw_text
    assert "ROLE:" in cat.master_raw_text or any(l.label.upper().startswith("ROLE") for l in cat.master_layers)
    layers = master_raw_to_db_layers(cat.master_raw_text, cat.workflow)
    keys = [layer["key"] for layer in layers]
    assert "subject_insert" in keys
    assert any(layer.get("type") == "text" for layer in layers)


def test_dynamic_header_parsing():
    block = "ROLE: You are a jeweler.\n\nCAMERA & RENDERING: Studio lighting.\n\nAVOID: blur"
    raw, layers = parse_labeled_sections(block)
    assert raw
    labels = [l["label"] for l in layers]
    assert any("ROLE" in lbl for lbl in labels)
    assert any(l["type"] == "negative" for l in layers)


def test_fourteen_jewelry_subjects_in_catalog():
    cat = next(w for w in load_all_prompt_files() if w.workflow == "CATALOG_IMAGE")
    assert len(cat.children) == 14
    assert cat.child_raw_text
    assert "Ring" in cat.child_raw_text
    assert "Kara" in cat.child_raw_text
    assert "UPRIGHT PRESENTATION LOCK" in cat.master_raw_text
    assert "never use cream velvet" in cat.master_raw_text.lower()
