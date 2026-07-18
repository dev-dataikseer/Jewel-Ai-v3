# How to edit & add Jewel AI prompts

This folder (`docs/Modals/Prompts/`) is the **file-based seed library**. After import, prompts live in the database and show in **Admin → Prompts**.

---

## Where prompts appear in the UI

| What | Admin location | Files here |
|------|----------------|------------|
| Workflow master (Catalog, Try-On, …) | **Prompt Editor** → select workflow → **Master Prompt** | `*_master.txt` |
| Jewelry type (Ring, Necklace, …) | **Prompt Editor** → select workflow → pick type | `ring.txt`, `necklace.txt`, … |
| Shared blocks (lock, branding, env pool) | **Shared prompt fragments** (below Prompt Editor) | `RAW_*.txt`, `EXEC_*.txt`, `BRAND_*.txt`, … |

After you save in Admin, the next generation job uses the new version immediately (no redeploy for text-only edits).

---

## One-time / refresh import (from these .txt files → DB)

From the `backend` folder:

```powershell
cd "d:\Workspace\Jewel AI\Jewel AI\backend"
.\.venv\Scripts\python.exe -m seeds.import_prompts_folder --force
```

Without `--force`, unchanged text is skipped. With `--force`, every file creates a new active version.

On API startup, seeds also run a non-force import so empty DBs get these prompts.

---

## How to CHANGE an existing prompt (recommended)

### Option A — Admin UI (preferred for day-to-day)

1. Open **Admin → Prompts**
2. **Masters / jewelry types:** choose workflow + “Master Prompt” or a jewelry type → edit → **Save**
3. **Shared fragments:** scroll to **Shared prompt fragments** → pick a block → edit → **Save new version**
4. Optional: **Prompt Test** tab to preview compose output

### Option B — Edit the .txt file, then re-import

1. Edit the matching file in this folder (see tables below)
2. Run `python -m seeds.import_prompts_folder --force`
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
5. Run import with `--force`
6. Confirm it appears under **Shared prompt fragments**

If you only need a one-off line for a workflow, prefer editing that workflow’s **Master Prompt** in Admin instead of adding a fragment.

---

## How to ADD a new jewelry type subject

1. Add file e.g. `docs/Modals/Prompts/tiara.txt` with the grounding sentence
2. Add the display name to `backend/seeds/prompts_data.py` → `JEWELRY_TYPES`
3. Map file → label in `import_prompts_folder.py` → `SUBJECT_FILE_MAP`  
   e.g. `"tiara": "Tiara"`
4. Run import `--force`
5. In Admin Prompt Editor, select a workflow → choose **Tiara** → confirm text

---

## How to ADD / change a workflow master

1. Edit or create `WORKFLOW_ID_master.txt` (example: `CATALOG_IMAGE_master.txt`)
2. Map in `import_prompts_folder.py` → `MASTER_FILE_MAP`
3. Ensure workflow exists in `prompts_data.py` / Studio sidebar
4. Run import `--force`
5. Open Admin → that workflow → **Master Prompt**

Master templates may include placeholders the engine fills later:

| Placeholder | Meaning |
|-------------|---------|
| `{{SUBTYPE_BLOCK}}` | Jewelry-type subject text(s) |
| `{{EXECUTION_BLOCK}}` | Catalog mode fragment (modern / mirror / style) |
| `{{BRANDING_CLAUSE}}` | Logo × reference branding fragment |
| `{{CHOSEN_ENVIRONMENT}}` | One line from environment pool (rotated) |
| `{{PLACEMENT_ANATOMY}}` | Try-on placement line for jewelry type |
| `{{TRYON_MODE_CLAUSE}}` | Customer preserve clause when tryOnMode=customer |
| `{{USER_CUSTOM_INSTRUCTION}}` / `{{USER_ADDITION_TEXT}}` | User free text |
| `{{LOGO_IMAGE_INDEX}}` | Image index for logo slot |
| `{{THEME_LINE}}` / `{{LOGO_LINE}}` | Optional attachment lines |

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

### Shared fragments (Admin “Shared prompt fragments”)
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
| `ATTACH_PRIMARY_SUBJECT.txt` | `ATTACH_PRIMARY_SUBJECT` |
| `ATTACH_ENVIRONMENT_REFERENCE.txt` | `ATTACH_ENVIRONMENT_REFERENCE` |
| `ATTACH_LOGO.txt` | `ATTACH_LOGO` |
| `ATTACH_TRYON_PERSON.txt` | `ATTACH_TRY_ON` |
| `BACKGROUND_SOURCE_*.txt` | same name |
| `CUSTOM_*.txt` | same name |
| `TRYON_*.txt` | same name |
| `MULTI_ITEM_FRAME.txt` | `MULTI_ITEM_FRAME` |
| `USER_ADDITION_WRAP.txt` | `USER_ADDITION_WRAP` |
| `ENVIRONMENT_POOL.txt` | one environment per line |

---

## Template: new fragment file

```text
YOUR INSTRUCTION HERE. Keep Image 1 jewelry identity locked.
Use placeholders only when the engine fills them, e.g. {{CHOSEN_ENVIRONMENT}}.
```

## Template: new jewelry subject

```text
The [piece] rests / hangs / sits according to real physics from Image 1.
Generate a correct contact shadow. Preserve scale and orientation exactly.
```

## Template: new workflow master

```text
ROLE: You are …

CAMERA: …

LIGHTING: …

{{SUBTYPE_BLOCK}}

INSTRUCTION: …

NEGATIVE PROMPT: …
```

---

## Rules of thumb

1. **Never hardcode creative prompt sentences in Python** — use this folder or Admin.
2. **Preserve placeholders** the assembler injects.
3. Prefer **Admin Save** for quick tweaks; use **.txt + import --force** when you want Git-tracked seeds.
4. Redeploy API/worker after code changes; text-only Admin edits do not need a redeploy.
5. Use **Prompt Test** after big wording changes before bulk jobs.
