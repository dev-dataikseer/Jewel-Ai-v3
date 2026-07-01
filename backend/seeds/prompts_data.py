"""Workflow and jewelry-type metadata for Jewel AI Studio.

All actual prompt content lives in the database (prompt_master_templates/versions,
prompt_subjects/versions, prompt_variants/versions) and is managed via the Admin UI.

The prompts/*.txt files are imported into the DB once via `python -m seeds.migrate_prompt_txt`.
After migration, the database is the sole source of truth — managed via the Admin UI.

This module provides only structural metadata — workflow definitions and jewelry
type labels — used by seed scripts, the validator, and the /config/options endpoint.
"""

WORKFLOWS: list[dict[str, str | bool]] = [
    {"id": "CATALOG_IMAGE", "label": "Catalog Image", "requires_reference": False, "bulk": True},
    {"id": "JEWELRY_ON_MODEL", "label": "Jewelry On Model", "requires_reference": True, "bulk": False},
    {"id": "GEMSTONE_COLOR_CHANGE", "label": "Gemstone Color Change", "requires_reference": False, "bulk": True},
    {"id": "CUSTOMER_TRY_ON", "label": "Customer Try-On", "requires_reference": True, "bulk": False},
    {"id": "REFERENCE_STYLE_MATCH", "label": "Style from Reference", "requires_reference": True, "bulk": False},
    {"id": "BACKGROUND_REPLACEMENT", "label": "Background Replacement", "requires_reference": False, "bulk": False},
    {"id": "LUXURY_ENHANCEMENT", "label": "Luxury Enhancement", "requires_reference": False, "bulk": False},
    {"id": "CUSTOM_PROMPT", "label": "Custom Prompt", "requires_reference": False, "bulk": False},
    {"id": "BULK_GENERATION", "label": "Bulk Generation", "requires_reference": False, "bulk": True},
    {"id": "RATE_TOOLS", "label": "Rate Tools", "requires_reference": False, "bulk": False},
]

JEWELRY_TYPES: list[str] = [
    "Ring",
    "Necklace",
    "Bangles",
    "Bracelet",
    "Earrings (Studs)",
    "Earrings (Drops)",
    "Earrings (Hoops)",
    "Pendant",
    "Watch",
    "Brooch",
    "Anklet",
    "Cufflinks",
    "Multiple Items",
]
