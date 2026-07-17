"""Parse master/child prompt library from data/seed-prompt-templates/*.txt files."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.pipeline.layer_derive import (
    default_structural_config,
    derive_layers_from_raw_text,
    merge_structural_layers,
    parse_labeled_sections,
    slugify_key,
)

CHILD_TYPE_MAP = {
    "RING": "Ring",
    "NECKLACE": "Necklace",
    "BANGLES": "Bangles",
    "BRACELET": "Bracelet",
    "KARA": "Kara",
    "EARRINGS (STUDS)": "Earrings (Studs)",
    "EARRINGS (DROPS)": "Earrings (Drops)",
    "EARRINGS (HOOPS)": "Earrings (Hoops)",
    "PENDANT": "Pendant",
    "WATCH": "Watch",
    "BROOCH": "Brooch",
    "ANKLET": "Anklet",
    "CUFFLINKS": "Cufflinks",
    "MULTIPLE ITEMS": "Multiple Items",
}

FILE_WORKFLOW_MAP = {
    "01_catalog_image.txt": "CATALOG_IMAGE",
    "02_jewelry_on_model.txt": "JEWELRY_ON_MODEL",
    "03_gemstone_color_change.txt": "GEMSTONE_COLOR_CHANGE",
    "04_customer_try_on.txt": "CUSTOMER_TRY_ON",
    "05_reference_style_match.txt": "REFERENCE_STYLE_MATCH",
    "06_background_replacement.txt": "BACKGROUND_REPLACEMENT",
    "07_luxury_enhancement.txt": "LUXURY_ENHANCEMENT",
    "08_custom_prompt.txt": "CUSTOM_PROMPT",
    "09_bulk_generation.txt": "BULK_GENERATION",
}

WORKFLOWS_WITH_VARIANT_INSERT = {
    "GEMSTONE_COLOR_CHANGE",
    "BACKGROUND_REPLACEMENT",
    "LUXURY_ENHANCEMENT",
    "REFERENCE_STYLE_MATCH",
}


@dataclass
class ParsedLayer:
    key: str
    label: str
    content: str | None
    layer_type: str = "text"


@dataclass
class ParsedVariant:
    label: str
    variant_key: str
    prompt_text: str


@dataclass
class ParsedChild:
    jewelry_type: str
    raw_text: str = ""
    layers: list[ParsedLayer] = field(default_factory=list)


@dataclass
class ParsedWorkflow:
    workflow: str
    master_raw_text: str = ""
    master_layers: list[ParsedLayer] = field(default_factory=list)
    variants: list[ParsedVariant] = field(default_factory=list)
    children: list[ParsedChild] = field(default_factory=list)
    child_raw_text: dict[str, str] = field(default_factory=dict)
    child_layers: dict[str, list[ParsedLayer]] = field(default_factory=dict)


def _extract_section(text: str, start_marker: str, end_markers: list[str]) -> str:
    start = text.find(start_marker)
    if start == -1:
        return ""
    start += len(start_marker)
    end = len(text)
    for marker in end_markers:
        pos = text.find(marker, start)
        if pos != -1:
            end = min(end, pos)
    return text[start:end].strip()


def _dict_layers_to_parsed(layers: list[dict[str, Any]]) -> list[ParsedLayer]:
    parsed: list[ParsedLayer] = []
    for layer in layers:
        if layer.get("is_system"):
            continue
        parsed.append(
            ParsedLayer(
                key=str(layer.get("key", "")),
                label=str(layer.get("label", "")),
                content=layer.get("content"),
                layer_type=str(layer.get("type", "text")),
            )
        )
    return parsed


def _parse_variants(block: str) -> list[ParsedVariant]:
    variants: list[ParsedVariant] = []
    for line in block.splitlines():
        m = re.match(r"^\s*-\s*([^:]+):\s*(.+)$", line.strip())
        if not m:
            continue
        label = m.group(1).strip()
        prompt_text = m.group(2).strip()
        variants.append(ParsedVariant(label=label, variant_key=slugify_key(label), prompt_text=prompt_text))
    return variants


def _parse_children(block: str) -> list[ParsedChild]:
    children: list[ParsedChild] = []
    chunks = re.split(r"^---\s*(.+?)\s*---\s*$", block, flags=re.MULTILINE)
    for i in range(1, len(chunks), 2):
        raw_name = chunks[i].strip().upper()
        body = chunks[i + 1] if i + 1 < len(chunks) else ""
        jewelry_type = CHILD_TYPE_MAP.get(raw_name)
        if not jewelry_type:
            continue
        raw_text, layer_dicts = parse_labeled_sections(body.strip())
        if not raw_text and not layer_dicts:
            continue
        children.append(
            ParsedChild(
                jewelry_type=jewelry_type,
                raw_text=raw_text or body.strip(),
                layers=_dict_layers_to_parsed(layer_dicts),
            )
        )
    return children


def parse_prompt_file(path: Path, workflow: str) -> ParsedWorkflow:
    text = path.read_text(encoding="utf-8")
    master_block = _extract_section(
        text,
        "MASTER PROMPT",
        ["AVAILABLE TRANSFORMATION OPTIONS", "CHILD PROMPTS", "USAGE:"],
    )
    variant_block = _extract_section(text, "AVAILABLE TRANSFORMATION OPTIONS", ["CHILD PROMPTS"])
    child_block = _extract_section(text, "CHILD PROMPTS", [])

    master_raw, master_layer_dicts = parse_labeled_sections(master_block)
    master_layers = _dict_layers_to_parsed(master_layer_dicts)
    children = _parse_children(child_block)

    child_raw_text = {c.jewelry_type: c.raw_text for c in children}
    child_layers = {c.jewelry_type: c.layers for c in children}

    return ParsedWorkflow(
        workflow=workflow,
        master_raw_text=master_raw or master_block.strip(),
        master_layers=master_layers,
        variants=_parse_variants(variant_block),
        children=children,
        child_raw_text=child_raw_text,
        child_layers=child_layers,
    )


def parsed_layers_to_db_layers(
    layers: list[ParsedLayer] | list[dict[str, Any]],
    structural_config: list[dict[str, Any]] | None,
    *,
    scope: str = "master",
) -> list[dict[str, Any]]:
    """Convert parsed layers to DB layer array with structural insert points."""
    content: list[dict[str, Any]] = []
    for item in layers:
        if isinstance(item, ParsedLayer):
            content.append(
                {
                    "key": item.key,
                    "label": item.label,
                    "description": None,
                    "order": len(content) + 1,
                    "enabled": True,
                    "content": item.content,
                    "locked": False,
                    "type": item.layer_type,
                    "priority": "important",
                    "settings": None,
                    "is_system": False,
                }
            )
        else:
            content.append(dict(item))

    if scope == "master":
        return merge_structural_layers(content, structural_config, scope=scope)
    return content


def master_raw_to_db_layers(
    raw_text: str,
    workflow: str,
    structural_config: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    config = structural_config or default_structural_config(workflow)
    return derive_layers_from_raw_text(raw_text, workflow, scope="master", structural_config=config)


def child_raw_to_db_layers(raw_text: str) -> list[dict[str, Any]]:
    return derive_layers_from_raw_text(raw_text, "", scope="subject")


def resolve_prompts_directory() -> Path | None:
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    candidates = [
        repo_root / "data" / "seed-prompt-templates",
        repo_root / "prompts",  # legacy path
        Path.cwd() / "data" / "seed-prompt-templates",
        Path.cwd() / "prompts",
        Path.cwd().parent / "data" / "seed-prompt-templates",
    ]
    for path in candidates:
        if path.is_dir() and any(path.glob("*.txt")):
            return path
    return None


def load_all_prompt_files(prompt_dir: Path | None = None) -> list[ParsedWorkflow]:
    prompt_dir = prompt_dir or resolve_prompts_directory()
    if not prompt_dir:
        return []
    results: list[ParsedWorkflow] = []
    for filename, workflow in FILE_WORKFLOW_MAP.items():
        path = prompt_dir / filename
        if path.is_file():
            results.append(parse_prompt_file(path, workflow))
    return results


def library_content_hash(prompt_dir: Path | None = None) -> str:
    prompt_dir = prompt_dir or resolve_prompts_directory()
    if not prompt_dir:
        return ""
    digest = hashlib.sha256()
    for filename in sorted(FILE_WORKFLOW_MAP.keys()):
        path = prompt_dir / filename
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()
