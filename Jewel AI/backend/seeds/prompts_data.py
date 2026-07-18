"""Workflow and jewelry-type metadata for Jewel AI Studio.

All actual prompt content lives in the database (prompt_master_templates/versions,
prompt_subjects/versions, prompt_variants/versions, prompt_fragments/versions)
and is managed via the Admin UI.

This module provides only structural metadata — workflow definitions and jewelry
type labels — used by seed scripts, the validator, and the /config/options endpoint.
"""

WORKFLOWS: list[dict[str, str | bool]] = [
    {"id": "CATALOG_IMAGE", "label": "Catalog Image", "requires_reference": False, "bulk": True},
    {"id": "VIRTUAL_TRY_ON", "label": "Virtual Try-On", "requires_reference": True, "bulk": False},
    {"id": "GEMSTONE_COLOR_CHANGE", "label": "Gemstone Color Change", "requires_reference": False, "bulk": True},
    {"id": "BACKGROUND_REPLACEMENT", "label": "Background Replacement", "requires_reference": False, "bulk": False},
    {"id": "LUXURY_ENHANCEMENT", "label": "Luxury Enhancement", "requires_reference": False, "bulk": False},
    {"id": "CUSTOM_PROMPT", "label": "Custom Prompt", "requires_reference": False, "bulk": False},
    {"id": "RATE_TOOLS", "label": "Rate Tools", "requires_reference": False, "bulk": False},
    # Legacy aliases kept for history filters / old jobs (hidden from Studio sidebar via frontend)
    {"id": "JEWELRY_ON_MODEL", "label": "Jewelry On Model (legacy)", "requires_reference": True, "bulk": False},
    {"id": "CUSTOMER_TRY_ON", "label": "Customer Try-On (legacy)", "requires_reference": True, "bulk": False},
    {"id": "REFERENCE_STYLE_MATCH", "label": "Style from Reference (legacy)", "requires_reference": True, "bulk": False},
    {"id": "BULK_GENERATION", "label": "Bulk Generation (legacy)", "requires_reference": False, "bulk": True},
]

# Workflows shown as first-class in Admin / Studio (canonical)
CANONICAL_WORKFLOWS: list[str] = [
    "CATALOG_IMAGE",
    "VIRTUAL_TRY_ON",
    "GEMSTONE_COLOR_CHANGE",
    "BACKGROUND_REPLACEMENT",
    "LUXURY_ENHANCEMENT",
    "CUSTOM_PROMPT",
]

JEWELRY_TYPES: list[str] = [
    "Ring",
    "Necklace",
    "Bangles",
    "Bracelet",
    "Kara",
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
