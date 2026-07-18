"""Load default fragment text from docs/Modals/Prompts when present.

Runtime prefers active DB versions (Admin). These defaults bootstrap empty DBs
and tests. Prefer editing Admin UI or the .txt files + re-import — not this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# --- Fragment keys (frozen vocabulary — must match assembler) ---

FIDELITY_LOCK = "RAW_JEWELRY_FIDELITY_LOCK"
EXEC_REFERENCE_MIRROR = "EXEC_REFERENCE_MIRROR"
EXEC_MODERN_CATALOG = "EXEC_MODERN_CATALOG"
EXEC_STYLE_MOOD = "EXEC_STYLE_MOOD"
BRAND_REF_WITH_LOGO = "BRAND_REF_WITH_LOGO"
BRAND_REF_NO_LOGO = "BRAND_REF_NO_LOGO"
BRAND_CATALOG_WITH_LOGO = "BRAND_CATALOG_WITH_LOGO"
BRAND_CATALOG_NO_LOGO = "BRAND_CATALOG_NO_LOGO"
ATTACH_PRIMARY_SUBJECT = "ATTACH_PRIMARY_SUBJECT"
ATTACH_ENVIRONMENT_REFERENCE = "ATTACH_ENVIRONMENT_REFERENCE"
ATTACH_CATALOG_ROLE_MAP = "ATTACH_CATALOG_ROLE_MAP"
ATTACH_ARTIFACT_SCRUB = "ATTACH_ARTIFACT_SCRUB"
ATTACH_TRY_ON = "ATTACH_TRY_ON"
ATTACH_PRODUCT = "ATTACH_PRODUCT"
ATTACH_LOGO = "ATTACH_LOGO"
BACKGROUND_SOURCE_REF = "BACKGROUND_SOURCE_REF"
BACKGROUND_SOURCE_GENERATED = "BACKGROUND_SOURCE_GENERATED"
CUSTOM_PRESERVE = "CUSTOM_PRESERVE"
CUSTOM_REALISM = "CUSTOM_REALISM"
CUSTOM_ALTER_GUARD = "CUSTOM_ALTER_GUARD"
TRYON_CUSTOMER_PRESERVE = "TRYON_CUSTOMER_PRESERVE"
TRYON_PLACEMENT_ANATOMY = "TRYON_PLACEMENT_ANATOMY"
MULTI_ITEM_FRAME = "MULTI_ITEM_FRAME"
MULTI_ITEM_BLEND_GUARD = "MULTI_ITEM_BLEND_GUARD"
USER_ADDITION_WRAP = "USER_ADDITION_WRAP"
ENVIRONMENT_POOL = "ENVIRONMENT_POOL"

# File stem in docs/Modals/Prompts → fragment key
_FILE_TO_KEY: dict[str, str] = {
    "RAW_JEWELRY_FIDELITY_LOCK": FIDELITY_LOCK,
    "EXEC_REFERENCE_MIRROR": EXEC_REFERENCE_MIRROR,
    "EXEC_MODERN_CATALOG": EXEC_MODERN_CATALOG,
    "EXEC_STYLE_MOOD": EXEC_STYLE_MOOD,
    "BRAND_REF_LOGO": BRAND_REF_WITH_LOGO,
    "BRAND_REF_NOLOGO": BRAND_REF_NO_LOGO,
    "BRAND_NOREF_LOGO": BRAND_CATALOG_WITH_LOGO,
    "BRAND_NOREF_NOLOGO": BRAND_CATALOG_NO_LOGO,
    "ATTACH_PRIMARY_SUBJECT": ATTACH_PRIMARY_SUBJECT,
    "ATTACH_ENVIRONMENT_REFERENCE": ATTACH_ENVIRONMENT_REFERENCE,
    "ATTACH_CATALOG_ROLE_MAP": ATTACH_CATALOG_ROLE_MAP,
    "ATTACH_ARTIFACT_SCRUB": ATTACH_ARTIFACT_SCRUB,
    "ATTACH_LOGO": ATTACH_LOGO,
    "ATTACH_TRYON_PERSON": ATTACH_TRY_ON,
    "ATTACH_PRODUCT": ATTACH_PRODUCT,
    "BACKGROUND_SOURCE_REF": BACKGROUND_SOURCE_REF,
    "BACKGROUND_SOURCE_GENERATED": BACKGROUND_SOURCE_GENERATED,
    "CUSTOM_PRESERVE": CUSTOM_PRESERVE,
    "CUSTOM_REALISM": CUSTOM_REALISM,
    "CUSTOM_ALTER_GUARD": CUSTOM_ALTER_GUARD,
    "TRYON_CUSTOMER_PRESERVE": TRYON_CUSTOMER_PRESERVE,
    "TRYON_PLACEMENT_ANATOMY": TRYON_PLACEMENT_ANATOMY,
    "MULTI_ITEM_FRAME": MULTI_ITEM_FRAME,
    "MULTI_ITEM_BLEND_GUARD": MULTI_ITEM_BLEND_GUARD,
    "USER_ADDITION_WRAP": USER_ADDITION_WRAP,
    "ENVIRONMENT_POOL": ENVIRONMENT_POOL,
}

FRAGMENT_KEYS: list[str] = [
    FIDELITY_LOCK,
    EXEC_REFERENCE_MIRROR,
    EXEC_MODERN_CATALOG,
    EXEC_STYLE_MOOD,
    BRAND_REF_WITH_LOGO,
    BRAND_REF_NO_LOGO,
    BRAND_CATALOG_WITH_LOGO,
    BRAND_CATALOG_NO_LOGO,
    ATTACH_PRIMARY_SUBJECT,
    ATTACH_ENVIRONMENT_REFERENCE,
    ATTACH_CATALOG_ROLE_MAP,
    ATTACH_ARTIFACT_SCRUB,
    ATTACH_TRY_ON,
    ATTACH_PRODUCT,
    ATTACH_LOGO,
    BACKGROUND_SOURCE_REF,
    BACKGROUND_SOURCE_GENERATED,
    CUSTOM_PRESERVE,
    CUSTOM_REALISM,
    CUSTOM_ALTER_GUARD,
    TRYON_CUSTOMER_PRESERVE,
    TRYON_PLACEMENT_ANATOMY,
    MULTI_ITEM_FRAME,
    MULTI_ITEM_BLEND_GUARD,
    USER_ADDITION_WRAP,
    ENVIRONMENT_POOL,
]

FRAGMENT_LABELS: dict[str, str] = {
    FIDELITY_LOCK: "Raw Jewelry Fidelity Lock",
    EXEC_REFERENCE_MIRROR: "Execution — Reference Mirroring",
    EXEC_MODERN_CATALOG: "Execution — Modern Dynamic Catalog",
    EXEC_STYLE_MOOD: "Execution — Style Mood Match",
    BRAND_REF_WITH_LOGO: "Branding — Reference + Logo",
    BRAND_REF_NO_LOGO: "Branding — Reference Cleanup (no logo)",
    BRAND_CATALOG_WITH_LOGO: "Branding — Catalog + Logo (no theme)",
    BRAND_CATALOG_NO_LOGO: "Branding — Catalog No Logo",
    ATTACH_PRIMARY_SUBJECT: "Attachment — Primary Subject (Image 1)",
    ATTACH_ENVIRONMENT_REFERENCE: "Attachment — Environment Reference",
    ATTACH_CATALOG_ROLE_MAP: "Attachment — Catalog Role Map (composed)",
    ATTACH_ARTIFACT_SCRUB: "Attachment — Artifact Scrub",
    ATTACH_TRY_ON: "Attachment — Try-On Person",
    ATTACH_PRODUCT: "Attachment — Product Only",
    ATTACH_LOGO: "Attachment — Logo Line",
    BACKGROUND_SOURCE_REF: "Background Source — From Reference",
    BACKGROUND_SOURCE_GENERATED: "Background Source — Generated",
    CUSTOM_PRESERVE: "Custom Prompt — Preserve Slot",
    CUSTOM_REALISM: "Custom Prompt — Physical Realism",
    CUSTOM_ALTER_GUARD: "Custom Prompt — Alter Guard (not sent to model)",
    TRYON_CUSTOMER_PRESERVE: "Try-On — Customer Photo Preserve",
    TRYON_PLACEMENT_ANATOMY: "Try-On — Placement Anatomy Lookup",
    MULTI_ITEM_FRAME: "Multi-Item Frame Header",
    MULTI_ITEM_BLEND_GUARD: "Multi-Item Blend Guard",
    USER_ADDITION_WRAP: "User Addition Wrapper",
    ENVIRONMENT_POOL: "Environment Rotation Pool",
}

# {{KEY}} tokens filled by the prompt engine at compose time (not runtime Jinja).
# Admin master/subject saves must allow these in stored prompt text.
PROMPT_PLACEHOLDERS: frozenset[str] = frozenset(
    {
        "SUBTYPE_BLOCK",
        "EXECUTION_BLOCK",
        "BRANDING_CLAUSE",
        "CHOSEN_ENVIRONMENT",
        "PLACEMENT_ANATOMY",
        "TRYON_MODE_CLAUSE",
        "USER_CUSTOM_INSTRUCTION",
        "USER_ADDITION_TEXT",
        "USER_INSTRUCTION",
        "LOGO_IMAGE_INDEX",
        "LOGO_LABEL",
        "THEME_LINE",
        "LOGO_LINE",
        "CUSTOM_PRESERVE",
        "CUSTOM_REALISM",
        "BACKGROUND_SOURCE",
        "TARGET_COLOR",
        "PRODUCT_INDEX",
    }
)


def _prompts_dir() -> Path:
    # backend/app/prompt_engine → Jewel AI/docs/Modals/Prompts
    return Path(__file__).resolve().parents[3] / "docs" / "Modals" / "Prompts"


def _load_from_files() -> tuple[dict[str, str], list[str]]:
    """Load fragment text + environment pool lines from docs/Modals/Prompts."""
    root = _prompts_dir()
    loaded: dict[str, str] = {}
    env_pool: list[str] = []
    if not root.is_dir():
        return loaded, env_pool

    for stem, key in _FILE_TO_KEY.items():
        path = root / f"{stem}.txt"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").strip()
        if key == ENVIRONMENT_POOL:
            env_pool = [
                ln.strip()
                for ln in text.splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
            loaded[key] = json.dumps(env_pool, indent=2)
        else:
            loaded[key] = text

    # Prefer seeded catalog role map; else compose from primary + placeholders.
    if ATTACH_CATALOG_ROLE_MAP not in loaded:
        primary = loaded.get(ATTACH_PRIMARY_SUBJECT, "")
        if primary:
            loaded[ATTACH_CATALOG_ROLE_MAP] = (
                "ATTACHMENT ROLES & INSTRUCTIONS:\n"
                f"{primary}"
                "{{THEME_LINE}}"
                "{{LOGO_LINE}}"
            )
    return loaded, env_pool


_FILE_FRAGMENTS, _FILE_ENV_POOL = _load_from_files()

DEFAULT_ENVIRONMENT_POOL: list[str] = _FILE_ENV_POOL or [
    "a matte travertine stone slab, soft architectural shadow lines crossing the surface at a low camera angle",
    "dark brushed concrete lit from one direction, casting a long soft-edged shadow across the frame",
    "fluted cream marble with vertical channel grooves catching diffuse overhead light",
    "a dark glass surface with caustic water reflections rippling across the background",
    "smooth grey river stones arranged with generous negative space around the jewelry",
    "dark volcanic basalt with a fine mist of water droplets catching specular highlights",
    "raw unbleached silk drapery pooling softly beneath the jewelry, natural fiber texture visible",
    "a frosted acrylic plinth lit from below with a cool rim light separating subject from background",
    "a brushed champagne-gold metal surface with a soft gradient reflection of the jewelry piece",
]

# Fallback prose if a file is missing (tests / partial installs)
_FALLBACK: dict[str, str] = {
    FIDELITY_LOCK: (
        "ABSOLUTE PRESERVATION LOCK: The jewelry piece shown in Image 1 must be reproduced "
        "with zero alteration to its physical identity."
    ),
    ATTACH_ARTIFACT_SCRUB: (
        "Exclude source watermarks, weight labels, price tags, and burned-in overlay text."
    ),
    ATTACH_PRODUCT: (
        "ATTACHED IMAGES: Image {{PRODUCT_INDEX}} is the jewelry product — "
        "preserve geometry, materials, and design exactly."
    ),
    MULTI_ITEM_BLEND_GUARD: "Ensure item properties do not blend across pieces.",
    ATTACH_CATALOG_ROLE_MAP: (
        "ATTACHMENT ROLES & INSTRUCTIONS:\n"
        "- Image 1: PRIMARY SUBJECT. The jewelry piece to preserve exactly."
        "{{THEME_LINE}}"
        "{{LOGO_LINE}}"
    ),
}

DEFAULT_FRAGMENTS: dict[str, str] = {**_FALLBACK, **_FILE_FRAGMENTS}
if ENVIRONMENT_POOL not in DEFAULT_FRAGMENTS:
    DEFAULT_FRAGMENTS[ENVIRONMENT_POOL] = json.dumps(DEFAULT_ENVIRONMENT_POOL, indent=2)


def substitute(template: str, variables: dict[str, Any]) -> str:
    """Replace {{KEY}} placeholders. Unknown keys left as empty string."""
    out = template or ""
    # Aliases for user-addition wrappers
    if "USER_INSTRUCTION" in variables and "USER_ADDITION_TEXT" not in variables:
        variables = {**variables, "USER_ADDITION_TEXT": variables["USER_INSTRUCTION"]}
    if "USER_ADDITION_TEXT" in variables and "USER_INSTRUCTION" not in variables:
        variables = {**variables, "USER_INSTRUCTION": variables["USER_ADDITION_TEXT"]}
    for key, value in variables.items():
        token = "{{" + key + "}}"
        out = out.replace(token, "" if value is None else str(value))
    while "{{" in out and "}}" in out:
        start = out.find("{{")
        end = out.find("}}", start)
        if start < 0 or end < 0:
            break
        out = out[:start] + out[end + 2 :]
    return out.strip()
