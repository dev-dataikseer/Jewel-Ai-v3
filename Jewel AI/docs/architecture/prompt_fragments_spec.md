# Prompt fragments & workflow consolidation (spec lock)

> Companion to `jewel_ai_prompt_engine_architecture.md` and `jewel_ai_workflow_prompts.md`.

## Principle

**Python may contain keys, flags, and substitution logic. Creative prompt sentences live in Admin/DB.**

## Canonical workflows

| ID | Modes |
|---|---|
| `CATALOG_IMAGE` | `catalogMode`: `modern` \| `reference_mirror` \| `style_mood` |
| `VIRTUAL_TRY_ON` | `tryOnMode`: `studio` \| `customer` |
| `GEMSTONE_COLOR_CHANGE` | — |
| `BACKGROUND_REPLACEMENT` | — |
| `LUXURY_ENHANCEMENT` | — |
| `CUSTOM_PROMPT` | — |

Aliases resolved in [`workflow_resolve.py`](../../backend/app/prompt_engine/workflow_resolve.py).

## Fragment keys

Defined in [`fragment_defaults.py`](../../backend/app/prompt_engine/fragment_defaults.py), stored in `prompt_fragments` / `prompt_fragment_versions`, edited via Admin → Prompts → Shared prompt fragments (`GET/POST /prompts/fragments`).

## Assembler order

1. Compose master + subjects + variants (DB)
2. Bookend `RAW_JEWELRY_FIDELITY_LOCK`
3. Catalog: inject execution fragment by `catalogMode` + branding by `has_logo`
4. Try-on customer: inject `TRYON_CUSTOMER_PRESERVE`
5. Custom: Change slot (guarded) + Preserve + Realism fragments
6. Background: `BACKGROUND_SOURCE_*`
7. Attachment fragments
8. Model adapter (char budget only)

## Model note (FASHN)

Default try-on endpoint is **Nano Banana Pro Edit** (compositing). Garment VTON models remain optional advanced picks; they are not jewelry-capable defaults.
