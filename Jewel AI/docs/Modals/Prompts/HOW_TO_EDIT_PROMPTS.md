# How to edit & add Jewel AI prompts

**Admin UI is the source of truth.** Day-to-day edits happen in **Admin → Prompts**. This folder (`docs/Modals/Prompts/`) is a **migration / disaster-recovery** seed library only — not the runtime hot path.

See also: [PROMPT_ENGINE_AUDIT.md](../../architecture/PROMPT_ENGINE_AUDIT.md) and [PROMPT_PIPELINE.md](../../architecture/PROMPT_PIPELINE.md).

---

## Where prompts appear in the UI

| What | Admin location | Files here (migration only) |
|------|----------------|------------------------------|
| Workflow master (Catalog, Try-On, …) | **Prompts → Workflow prompts** → Master | `*_master.txt` |
| Jewelry type (Ring, Necklace, …) | **Prompts → Workflow prompts** → type | `ring.txt`, `necklace.txt`, … |
| Shared blocks (lock, branding, env pool) | **Prompts → Shared fragments** | `RAW_*.txt`, `EXEC_*.txt`, `BRAND_*.txt`, … |
| Style presets | **Prompts → Style presets** | (Admin-only; not file-seeded) |
| Import / placeholders | **Prompts → Tools** | — |

Studio Settings exposes an **Additional instruction (optional)** field only — a sanitized user add-on. Master prompts are never edited from Studio.

After you save in Admin, the next generation job uses the new version immediately (no redeploy for text-only edits). Use **Validate** before save; **Preview** to dry-run compose; **Versions** to activate/rollback.

---

## One-time / refresh import (from these .txt files → DB)

**Preferred:** Admin → Prompts → **Tools** → **Import from files**.

CLI (ops / local only):

```powershell
cd "d:\Workspace\Jewel AI\Jewel AI\backend"
$env:ALLOW_PROMPT_RESEED = "true"
.\.venv\Scripts\python.exe -m seeds.import_prompts_folder --force
```

Without `--force`, unchanged text is skipped. With `--force`, every file can create a new active version.

**Production:** keep `ALLOW_PROMPT_RESEED` unset or `false` on Railway. Boot no longer auto-imports this folder (avoids `Prompts folder not found` in containers that omit `docs/`).

---

## How to CHANGE an existing prompt (recommended)

### Option A — Admin UI (preferred)

1. Open **Admin → Prompts**
2. **Workflow prompts:** choose workflow + Master / jewelry type / variant → edit → **Validate** → **Save**
3. **Shared fragments:** select a block → edit → **Save new version**
4. **Preview:** use Compose preview on Workflow prompts (Admin-only assemble API)
5. **Rollback:** open **Versions** → **Activate** an older version

### Option B — Edit the .txt file, then re-import (migration only)

1. Edit the matching file in this folder (see tables below)
2. Import via Admin Tools or CLI with `ALLOW_PROMPT_RESEED=true`
3. Refresh Admin — you should see the new text

---

## How to ADD a new shared fragment

1. Create a new file: `docs/Modals/Prompts/MY_NEW_BLOCK.txt`
2. Put plain prompt text inside (UTF-8). Use placeholders if code will fill them:

```text
Place the piece into this setting: {{CHOSEN_ENVIRONMENT}}
```

3. Register the file in two places (developer step):
   - `backend/seeds/import_prompts_folder.py` → `FRAGMENT_FILE_MAP`
   - `backend/app/prompt_engine/fragment_defaults.py` → `_FILE_TO_KEY` + `FRAGMENT_KEYS` + `FRAGMENT_LABELS`
4. Wire the key in the assembler (`execution_mode.py` / `attachments.py` / `engine.py`) if it should be injected automatically
5. Import with `--force` (or Admin Tools)
6. Confirm it appears under **Shared fragments**

If you only need a one-off line for a workflow, prefer editing that workflow’s **Master Prompt** in Admin instead of adding a fragment.

---

## How to ADD a new jewelry type subject

1. Add file e.g. `docs/Modals/Prompts/tiara.txt` with the grounding sentence
2. Add the display name to `backend/seeds/prompts_data.py` → `JEWELRY_TYPES`
3. Map file → label in `import_prompts_folder.py` → `SUBJECT_FILE_MAP`  
   e.g. `"tiara": "Tiara"`
4. Import `--force`
5. In Admin → Workflow prompts, select a workflow → choose **Tiara** → confirm text

---

## Placeholder contract

Keep `{{TOKENS}}` exactly as documented in Admin → Tools → Placeholder reference. Unknown placeholders fail Admin **Validate** / save. Studio users must not use `{{` in the add-on (sanitized server-side).

---

## How to ADD / change a workflow master

1. Edit or create `WORKFLOW_ID_master.txt` (example: `CATALOG_IMAGE_master.txt`)
2. Map in `import_prompts_folder.py` → `MASTER_FILE_MAP`
3. Ensure workflow exists in `prompts_data.py` / Studio sidebar
4. Import `--force` (or Admin Tools)
5. Open Admin → Workflow prompts → that workflow → **Master Prompt**

Do **not** delete placeholders the code expects, or that slot will be blank.

---

## File map (this folder)

### Masters
| File | Workflow |
|------|----------|
| `CATALOG_IMAGE_master.txt` | Catalog Image |
| `VIRTUAL_TRY_ON_master.txt` | Virtual Try-On |
| `GEMSTONE_COLOR_CHANGE_master.txt` | Gemstone Color Change |
| `BACKGROUND_REPLACEMENT_master.txt` | Background Replacement |
| `LUXURY_ENHANCEMENT_master.txt` | Luxury Enhancement |
| `CUSTOM_PROMPT_master.txt` | Custom Prompt |

### Jewelry subjects
| File | Studio label |
|------|----------------|
| `ring.txt` | Ring |
| `necklace.txt` | Necklace |
| `bracelet.txt` | Bracelet |
| `bangle.txt` | Bangles |
| `kara.txt` | Kara |
| `earring_stud.txt` | Earrings (Studs) |
| `earring_drop.txt` | Earrings (Drops) |
| `earring_hoop.txt` | Earrings (Hoops) |
| `pendant.txt` | Pendant |
| `watch.txt` | Watch |
| `brooch.txt` | Brooch |
| `anklet.txt` | Anklet |
| `cufflinks.txt` | Cufflinks |
| `multiple_items.txt` | Multiple Items |

### Shared fragments
| File | DB key |
|------|--------|
| `RAW_JEWELRY_FIDELITY_LOCK.txt` | `RAW_JEWELRY_FIDELITY_LOCK` |
| `EXEC_REFERENCE_MIRROR.txt` | `EXEC_REFERENCE_MIRROR` |
| `EXEC_MODERN_CATALOG.txt` | `EXEC_MODERN_CATALOG` |
| `EXEC_STYLE_MOOD.txt` | `EXEC_STYLE_MOOD` |
| `BRAND_REF_LOGO.txt` | `BRAND_REF_WITH_LOGO` |
| `BRAND_REF_NOLOGO.txt` | `BRAND_REF_NO_LOGO` |
| `BRAND_NOREF_LOGO.txt` | `BRAND_CATALOG_WITH_LOGO` |
| `BRAND_NOREF_NOLOGO.txt` | `BRAND_CATALOG_NO_LOGO` |
| `ATTACH_*.txt` / `BACKGROUND_*.txt` / `CUSTOM_*.txt` / `TRYON_*.txt` | same or mapped keys |
| `MULTI_ITEM_FRAME.txt` | `MULTI_ITEM_FRAME` |
| `USER_ADDITION_WRAP.txt` | `USER_ADDITION_WRAP` |
| `ENVIRONMENT_POOL.txt` | one environment per line |

---

## Rules of thumb

1. **Never hardcode creative prompt sentences in Python** — use Admin or this folder (migration).
2. **Preserve placeholders** the assembler injects; Admin Validate catches unknown tokens.
3. Prefer **Admin Save** for day-to-day tweaks; use **.txt + import** when you want Git-tracked seeds.
4. Redeploy API/worker after code changes; text-only Admin edits do not need a redeploy.
5. Use **Compose preview** after big wording changes before bulk jobs.

---

## Archived CLI helpers

These remain in the repo for historical migrations but are **not** the day-to-day path:

- `backend/seeds/prompt_txt_import.py`
- `backend/seeds/migrate_prompt_txt.py`

Prefer Admin Tools import or `seeds.import_prompts_folder`.
