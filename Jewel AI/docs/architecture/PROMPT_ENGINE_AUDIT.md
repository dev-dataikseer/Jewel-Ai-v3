# Prompt Engine Audit

**Date:** 2026-07-22  
**Scope:** Runtime compose, Admin write path, Studio user add-on, file/seed bypasses  
**Verdict:** Skeleton is industry-aligned; multiple writers to “truth” and hot-path file fallbacks are not.

---

## Executive summary

Jewel AI already uses a **strong production pattern**:

- Versioned **Master → Subject → Variant** layers
- Shared **Fragments** (fidelity, branding, execution modes, attachments)
- **Python-routed** catalog execution modes (not prompt `if/else`)
- **Model adaptation** / capacity packing before fal.ai

That matches how serious multimodal products structure prompts: a registry of templates, runtime variable injection, and application-owned routing.

What was **not** industry-standard:

| Issue | Risk |
| --- | --- |
| DB + boot file import + import-time `.txt` + `_FALLBACK` | Silent drift; Admin edits ignored |
| `layers.py` reading `DEFAULT_FRAGMENTS` | Hot-path bypass of Admin DB |
| No save-time placeholder lint | Broken `{{TOKENS}}` only fail at generate |
| Admin UX: buried fragments, no preview/rollback | Operators cannot safely ship prompts |

**Product decision (confirmed):** Admin owns all config prompts; Studio keeps an optional sanitized **user add-on** (`prompt_text`, ≤500 chars).

---

## Scorecard

| Dimension | Industry norm | Jewel AI (before) | Target (this work) |
| --- | --- | --- | --- |
| Single source of truth | DB/registry at runtime | DB + files + fallbacks | **DB only at compose** |
| Versioning | Immutable versions + activate | DB versions; weak Admin UI | Versions + rollback UI |
| Placeholder contract | Validated registry | Documented; no save lint | **Lint on Admin save** |
| User free-text | Narrow sanitized add-on | Yes | **Keep** |
| Execution routing | Application code | `execution_mode.py` | Keep |
| Preview before deploy | Compose dry-run | API existed; UI missing | **Admin preview** |
| File import | One-time / explicit migration | Boot + Admin re-import | **Admin-only, explicit** |

---

## Confirmed findings

1. **Dual fragment path** — `get_fragment_text(db)` vs `layers.py` → `DEFAULT_FRAGMENTS` for `USER_ADDITION_WRAP` / multi-item frames.
2. **Boot auto-import** — `run_seeds.py` called `import_prompts_folder(force=False)`; Railway often logged `Prompts folder not found`.
3. **Orphan fragment keys** — `ATTACH_THEME_LINE_TEMPLATE`, `ATTACH_LOGO_LINE_TEMPLATE` imported but not in `FRAGMENT_KEYS`.
4. **`CUSTOM_ALTER_GUARD`** stored in DB while `custom_guard.py` used hardcoded regex.
5. **Variants** Admin-only (intentional; not file-seeded).
6. **Studio Prompt** is an add-on, not the master — labeling was ambiguous.

---

## Three prompt classes (canonical)

| Class | Owner | Storage | Example |
| --- | --- | --- | --- |
| Config templates | Admin | master / subject / fragment / variant versions | ROLE, preservation, try-on anatomy |
| Runtime variables | Python engine | Injected via `substitute()` | `{{CHOSEN_ENVIRONMENT}}`, `{{BRANDING_CLAUSE}}` |
| User add-on | Studio user | `GenerationJob.prompt_text` | “warmer lighting, minimal props” |

---

## Write vs read paths

**Allowed writes:** `RequireAdmin` → `POST /api/prompts/*` (templates, subjects, variants, fragments, presets).

**Allowed runtime user input:** sanitized `prompt_text` on `POST /jobs` / bulk; selection of Admin-authored variants / style presets / catalog mode.

**Removed from hot path:** compose-time `DEFAULT_FRAGMENTS`; startup `import_prompts_folder`.

**Kept as migration tool:** `POST /prompts/import-from-files` (Admin, explicit).

---

## Industry comparison (short)

| Practice | Alignment |
| --- | --- |
| Template registry + versions | Yes (DB) |
| Separate system vs user prompt slots | Yes (after clarification) |
| App-owned branching for modes | Yes (`execution_mode.py`) |
| Observability of composed prompt | Partial (`final_prompt` on job; Admin preview added) |
| External prompt ops SaaS (Langfuse, etc.) | Optional future — not required |

---

## Related docs

- [PROMPT_PIPELINE.md](./PROMPT_PIPELINE.md)
- [HOW_TO_EDIT_PROMPTS.md](../Modals/Prompts/HOW_TO_EDIT_PROMPTS.md)
- [jewel_ai_prompt_engine_architecture.md](./jewel_ai_prompt_engine_architecture.md)

---

## Implementation status (2026-07-22)

| Item | Status |
| --- | --- |
| DB-only fragment reads in `layers.py` | Done |
| Production file fallback gated (`ALLOW_PROMPT_FILE_FALLBACK`) | Done |
| Boot `import_prompts_folder` removed (opt-in reseed only) | Done |
| `POST /prompts/validate` | Done |
| Admin Prompts tabs (workflows / fragments / presets / tools) | Done |
| Compose preview + version activate/diff UI | Done |
| Fragment key hygiene + `CUSTOM_ALTER_GUARD` from DB | Done |
| Studio label: Additional instruction (optional) | Done |
| Docs + `test_prompt_validate.py` | Done |
| Railway `ALLOW_PROMPT_RESEED=false` | Confirmed |