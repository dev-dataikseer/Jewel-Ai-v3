# Jewel AI — Prompt Pipeline & Generation System

This document explains how prompts are built, stored, edited, and sent to fal.ai — from Admin layer edits through Studio job submission to the AI API.

---

## 1. High-level architecture

Jewel AI uses a **DB-driven, layer-based prompt pipeline**. At generation time, **every config prompt byte comes from PostgreSQL**. File seeds and `DEFAULT_FRAGMENTS` are not on the hot path.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│ Admin UI    │────▶│ POST /prompts/*  │────▶│ PostgreSQL      │     │              │
│ (write)     │     │ + /validate      │     │ (masters /      │     │              │
└─────────────┘     └──────────────────┘     │  subjects /     │     │              │
                                             │  fragments /    │     │              │
┌─────────────┐     ┌──────────────────┐     │  variants)      │────▶│ Composer     │──▶ fal.ai
│ Studio UI   │────▶│ POST /jobs       │────▶│ + prompt_text   │     │ (layers)     │
│ (add-on)    │     │ prompt_text only │     │   user add-on   │     │              │
└─────────────┘     └──────────────────┘     └─────────────────┘     └──────────────┘
```

See also: [PROMPT_ENGINE_AUDIT.md](PROMPT_ENGINE_AUDIT.md) for the scorecard and consolidation target.

**Three prompt classes (never mix):**

| Class | Owner | Storage |
|-------|-------|---------|
| **Config templates** | Admin | `prompt_*_versions` tables |
| **Runtime variables** | Python engine | Injected via `{{PLACEHOLDERS}}` |
| **User add-on** | Studio | `GenerationJob.prompt_text` (sanitized, ≤500 chars) |

**Three config pieces per workflow:**

| Piece | Stored as | Purpose |
|-------|-----------|---------|
| **Master** | `PromptMasterVersion.layers` | Workflow-wide rules: camera, lighting, preservation, negative prompt |
| **Subject (child)** | `PromptSubjectVersion.layers` per **workflow + jewelry type** | Type-specific anatomy, placement, physics — catalog vs try-on differ |
| **Variant** | `PromptVariantVersion.prompt_text` | Dropdown option text (background style, metal type, gemstone color) |

---

## 2. Where prompt text lives

### 2.1 Database (source of truth at runtime)

- **Master templates** — one per workflow (`CATALOG_IMAGE`, `CUSTOMER_TRY_ON`, etc.)
- **Subject prompts** — one per **(workflow, jewelry_type)** tuple — e.g. `CATALOG_IMAGE` + `Ring` vs `CUSTOMER_TRY_ON` + `Ring`
- **Variants** — per workflow dropdown value (e.g. `Cream Velvet` for background replacement)

Each master/subject has **versioned rows**. Saving in Admin creates a new version; you can activate older versions from version history.

### 2.2 File seeds (migration / disaster recovery only)

Text files under `docs/Modals/Prompts/` are **not** read during job generation and are **not** auto-imported on API boot.

- **First deploy:** `seed_prompt_fragments()` may create empty DB shells; content should come from Admin or an **explicit** import.
- **Admin → Prompts → Tools → Import from files:** explicit Admin action (`POST /prompts/import-from-files`). Prefer this over CLI for production recovery.
- **CLI (archived / ops):** `python -m seeds.import_prompts_folder` — only when `ALLOW_PROMPT_RESEED=true` (default **false** in production). Do not enable reseed on Railway for normal deploys.
- **File fallback at compose:** disabled in production unless `ALLOW_PROMPT_FILE_FALLBACK=true` (dev/tests only).

Versions with `source=admin` are never overwritten by import unless `force=true`.

### 2.4 Auth and roles

**Mandatory login:** The app requires authentication on load. Unauthenticated users are redirected to `/login`. Studio (`/`), History (`/history`), and Admin (`/admin`) are protected by an auth guard.

- **admin** — full Admin UI, prompt editing, user management, provider settings
- **user** — Studio and History only; Admin nav hidden; no prompt API write access

Default seed accounts: `admin@jewelai.com` / `changeme`, `studio@jewelai.com` / `studio123`.

On successful login, users land on **Studio** (`/`). Admin users can navigate to Admin from the header.

### 2.5 Providers (fal.ai only)

Image generation uses **fal.ai exclusively**. Legacy Gemini/OpenAI/Replicate providers are deactivated in the seed.

- Set `FAL_KEY` in `backend/.env` or via **Admin → Providers**
- Individual models are managed in **Admin → Models** (`ModelDefinition` catalog)
- Default provider endpoint: `fal-ai/nano-banana-pro/edit`

### 2.6 Code (metadata only)

`seeds/prompts_data.py` defines **workflows**, **jewelry types**, and **Studio dropdown options** — not composed prompt copy.

---

## 3. Layer model

Each master or subject is an **ordered array of layers** (JSON). Layer types:

| Type | Role |
|------|------|
| `text` | Free-form Jinja template rendered into the body |
| `insert_point` | **Master only** — where subject (child) layers are injected |
| `variant_insert` | Where the selected variant prompt is inserted (if user picked a dropdown) |
| `user_insert` | Where optional Studio “additional instruction” is inserted |
| `negative` | Rendered separately as **negative prompt** (not in main body) |

Example master layer order (typical):

1. System role (`text`)
2. Camera settings (`text`)
3. **Subject insert** (`insert_point`) ← Ring/Necklace/etc. layers go here
4. Environment (`text`)
5. Lighting & physics (`text`)
6. Preservation lock (`text`)
7. Variant insert (`variant_insert`) ← e.g. background style text
8. Negative prompt (`negative`)

### 3.1 Jinja variables

Layers can use placeholders filled at compose time:

| Variable | Source |
|----------|--------|
| `{{ jewelry_type }}` | Selected type(s) — single or comma-joined |
| `{{ metal_type }}` | Studio dropdown (Luxury Enhancement) |
| `{{ background_style }}` | Studio dropdown (Background / Reference workflows) |
| `{{ gemstone_target_color }}` | Studio dropdown (Gemstone Color Change) |
| `{{ lighting_style }}` | Studio optional field |
| `{{ prompt_text }}` | User’s additional instruction |
| `{{ variant_text }}` | Active variant layer content |
| `{{ workflow }}` | Workflow id |

Strict Jinja: undefined variables **fail composition** with a clear error — unresolved `{{` / `{%` are never sent to fal.ai.

Layers support `priority`: `critical` (never dropped), `important`, `optional`. Token budget drops optional first, then important; preservation lock and subject core are critical.

### 3.2 Composition modes

| Mode | Behavior |
|------|----------|
| `layered` (default) | Walk master layers in order; render each; inject subject at `insert_point` |
| `raw` | Use `raw_override` as entire body; only `negative` layers from master are kept |

---

## 4. Compose procedure (step by step)

When a job runs (or Admin clicks **Server preview**), `compose_prompt()` executes:

```
1. Parse jewelry_type
      "Ring, Necklace" → ["Ring", "Necklace"]
      empty → default ["Ring"]
      "Multiple Items" + other types → drop "Multiple Items", keep specifics

2. Load active master version for workflow
      → master_layers[], composition_mode, raw_override

3. For EACH jewelry type:
      Load active subject version for that type
      → append (type, subject_layers) to subject_layers_by_type

4. Resolve variant (if workflow has variant field):
      GEMSTONE_COLOR_CHANGE  → gemstone_target_color
      BACKGROUND_REPLACEMENT → background_style
      LUXURY_ENHANCEMENT     → metal_type
      REFERENCE_STYLE_MATCH  → background_style

5. Build variables dict (Jinja context)

6. assemble_layers()
      Walk sorted master layers
      At insert_point:
         • 1 type  → render that subject's layers
         • 2+ types → compositional framing ("Item 1: … Item 2: …")
      Apply token budget (~1200 words) — drops optional/important layers first; never drops critical (preservation lock, subject core)

7. Append style preset addon + lighting_style suffix (if set)

8. Merge negative: master negative layers + variant negative_addon

9. Return ComposedPrompt { text, negative_prompt, debug, version ids }
```

### 4.1 Post-compose augmentation (image slot map)

Before calling fal.ai, `build_final_prompt()` appends **image role hints** via `attachment_parts()` after `build_image_packet()` decides the ordered URLs:

| Slot order | Role | When |
|------------|------|------|
| Image 1 | Product (raw jewelry) | Always for I2I |
| Image 2 | Theme / style reference **or** portrait | Catalog theme; try-on portrait |
| Image 3+ | Shop logo | When model `max_images` has capacity |

| Workflow | Attachment text (summary) |
|----------|-------------------------|
| `CATALOG_IMAGE`, `BULK_GENERATION` | Image 1 = product. Image 2 = theme (if present). Logo image = place brand mark naturally. |
| `REFERENCE_STYLE_MATCH` | Image 1 = product. Image 2 = style reference. |
| `JEWELRY_ON_MODEL`, `CUSTOMER_TRY_ON` | Image 1 = jewelry. Image 2 = portrait. Logo only if a free slot remains. |

**Logo policy:** Prefer sending the logo as a fal reference (`logoMode=model`) so the model places it. If the model is single-image / out of capacity, fall back to `composite_logo_beneath` (`logoMode=compose`). Set `LOGO_FORCE_COMPOSE=1` to always use the bottom-bar fallback.

Assembly lives in `app/pipeline/image_packet.py` and is shared by single and bulk jobs.

### 4.2 What gets stored on the job

- `final_prompt` — packed text sent to fal.ai (master + jewelry subjects + attachments)
- `master_version_id`, `subject_version_id` (comma-separated if multi-type), `variant_version_id`
- `provider_metadata.promptDebug` — layer keys, word count, jewelry_types list
- `provider_metadata.imageRoles` — ordered `{index, role, url}` slot map
- `provider_metadata.logoMode` / `logoApplied` — `model` | `compose` | `omit` | `none`

---

## 5. Multi jewelry type selection

**Studio:** user can multi-select jewelry types when the raw photo contains multiple pieces (e.g. Ring + Bracelet).

**Payload:** `jewelry_type: "Ring, Bracelet"` (comma-separated string)

**Compose logic:**

1. Validator splits, dedupes, validates each against `JEWELRY_TYPES`
2. Composer loads **separate subject** for Ring and for Bracelet
3. At master `insert_point`, **both subject layer stacks are concatenated**:
   - Ring subject rendered with `jewelry_type = "Ring"`
   - Bracelet subject rendered with `jewelry_type = "Bracelet"`
4. Master layers use `jewelry_type = "Ring, Bracelet"` in Jinja

**Special case — "Multiple Items":**

- If user selects **only** `Multiple Items` → uses the dedicated "Multiple Items" subject block
- If user selects `Multiple Items` **with** specific types → `Multiple Items` is ignored; specific types win

**When to use which:**

| Selection | Subject prompts used |
|-----------|-------------------|
| Ring | Ring subject only |
| Ring + Necklace | Ring subject + Necklace subject (concatenated) |
| Multiple Items only | Multiple Items subject (ensemble wording) |

---

## 6. Admin: adding or updating layers

### 6.1 What happens when you save

1. Admin **Prompts** tab → pick workflow + piece (Master / Ring / variant)
2. Edit layers (add, reorder, delete, change content or type)
3. **Save** → API creates a **new version row** and sets it active
4. Next job or preview uses the **new active version immediately** — no redeploy

### 6.2 Adding a new text layer

- Add layer in UI → set `key`, `label`, `order`, `type=text`, content with Jinja
- On next compose, assembler walks layers by `order` and includes new content
- **No code change required**

### 6.3 Adding a new layer type marker

- `insert_point` — only one recommended per master; marks where subjects inject
- `variant_insert` — master must include this layer for variant dropdown text to appear in body
- `user_insert` — explicit slot for user instruction (otherwise appended at end if present)

### 6.4 Reordering layers

Change `order` in Admin → compose order changes on next job. Token budget drops optional layers first; critical layers (preservation lock, subject core) are never removed.

### 6.5 Raw mode

Toggle master to **Raw override**: entire body comes from one textarea; negative layers still separate. Subject insert is skipped in raw mode.

### 6.6 Server preview

`GET /api/pipelines/{workflow}/assemble?jewelry_type=Ring` runs the same composer as production (without fal.ai call). Use this to verify layer changes before generating.

### 6.7 TXT re-import vs Admin edits

- If you edit `data/seed-prompt-templates/*.txt` and restart API → import may create **new DB versions** from files
- Admin edits and TXT import both create versions; **active version** wins
- Prefer Admin for iterative tuning; use TXT for bulk initial library load

---

## 7. Per-workflow behavior

Each workflow has its **own master template** and **own subject prompts per jewelry type** (`workflow` + `jewelry_type` in the DB). Catalog Ring and Try-On Ring are edited separately in Admin → Prompts.

| Workflow | Variant field | Typical images | Default fal model | Prompt focus |
|----------|---------------|----------------|-------------------|--------------|
| **CATALOG_IMAGE** | Style preset (optional addon) | Product photo | Nano Banana Pro Edit | Studio product shot, preservation lock |
| **BULK_GENERATION** | Same as catalog | Many product photos | Nano Banana Pro Edit | Batch catalog (same compose per job) |
| **JEWELRY_ON_MODEL** | — | Product + model portrait | FASHN Try-On v1.6 | Composite jewelry onto model |
| **CUSTOMER_TRY_ON** | — | Product + customer photo | image-apps-v2 VTON | Virtual try-on, preserve pose |
| **GEMSTONE_COLOR_CHANGE** | Gemstone target color | Product photo | FLUX Kontext | Change stone color only |
| **BACKGROUND_REPLACEMENT** | Background style | Product photo | FLUX Kontext | Replace surface/background |
| **LUXURY_ENHANCEMENT** | Metal type | Product photo | FLUX Kontext | Metal finish enhancement |
| **REFERENCE_STYLE_MATCH** | Background/style ref | Product + reference image | Nano Banana Pro Edit | Match reference aesthetic |
| **CUSTOM_PROMPT** | User-driven | Product (+ optional ref) | GPT Image 1.5 Edit | User instruction weighted |
| **RATE_TOOLS** | — | — | — | No image generation |

Studio users can override the default by selecting any catalog model from the **Parameters → AI Model** dropdown. Try-on workflows show only **Try-On** category models; catalog workflows hide VTON models.

Workflows with **variant dropdowns** insert variant text at the master's `variant_insert` layer when the user selects an option in Studio.

---

## 8. End-to-end: Studio click → fal.ai

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STUDIO                                                                        │
│  • Upload product image → Asset → job.input_url                               │
│  • Optional model/style reference → job.reference_url                         │
│  • Workflow, jewelry types[], variant dropdown, style preset                    │
│  • AI Model dropdown (fal catalog, grouped by category)                         │
│  • DynamicParamForm — model-specific params (aspect, num_images, resolution…)   │
│  • Optional prompt_text (additional instruction)                              │
│  • Job payload: model_endpoint_id + model_params (not legacy model_name)        │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ POST /api/jobs                                                                │
│  validate_job_create() — whitelist fields, parse jewelry types                │
│  Store GenerationJob with structured fields + provider_metadata             │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Worker: process_image_job                                                     │
│                                                                               │
│  A. compose_prompt(db, ComposeInput from job fields)                          │
│  B. augment_prompt_for_workflow(workflow, composed.text)                      │
│  C. Build image list: [input_url, reference_url]  (product first, person 2nd)│
│  D. GenerationRequest(prompt, negative_prompt, image_urls,                     │
│     model_endpoint_id, model_params)                                            │
│  E. route_generation() → FalAdapter.generate()                                │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ FAL ADAPTER                                                                   │
│                                                                               │
│  1. Upload local /uploads/... URLs to fal CDN if needed                       │
│  2. Truncate prompt if model has max_prompt_chars (e.g. Recraft = 1000)       │
│  3. Map images by model config:                                               │
│       • image_urls[]  — Nano Banana, GPT Image, FLUX.2, Seedream, Klein       │
│       • image_url     — FLUX Kontext, Recraft, Ideogram Remix, Bria FIBO      │
│       • try_on fields — FASHN, image-apps-v2, Kling, Cat-VTON, Leffa         │
│  4. Merge model default_params + Studio model_params (aspect, num_images, …)   │
│  5. fal_client.subscribe(endpoint, arguments={...})                           │
│  6. Download result image → save to /uploads/generated_*.png                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 8.1 Image + prompt pairing by workflow

| Workflow | Images sent (order) | fal payload shape |
|----------|---------------------|-------------------|
| Catalog / Bulk (+ optional theme + logo) | `[product, theme?, logo?]` | Multi-ref `image_urls[]` when capacity allows |
| Background / Gemstone / Luxury / Custom | `[product, logo?]` | `image_urls` or `image_url` per model |
| Reference style match | `[product, style_reference, logo?]` | Multi-ref `image_urls[]` |
| Jewelry on model / Customer try-on | `[product, portrait, logo?]` | VTON fields or ordered `image_urls`; logo only if capacity |
| Single-slot models (e.g. Kontext) | `[product]` | `image_url`; logo via post-compose fallback |

Prompt always describes **what to do**; images carry **what to preserve / brand**. Attachment text clarifies which image is which. Bulk jobs reuse the same packet builder as single jobs (shared theme/logo meta, per-product `input_url`).

### 8.2 Negative prompt

Sent separately when the model schema supports it. Built from:

- Master `negative` layers (Jinja rendered)
- Variant `negative_addon` (if any)

Not all fal models accept `negative_prompt` — adapter omits it when unsupported.

---

## 9. Model catalog (fal.ai image edit)

All models accept **image(s) + prompt** and return image(s). Categories filter in Studio by workflow.

### Catalog (13 models)

| Display name | Endpoint ID | Notes |
|--------------|-------------|-------|
| Nano Banana Pro Edit | `fal-ai/nano-banana-pro/edit` | Multi-ref, default for catalog |
| GPT Image 1.5 Edit | `fal-ai/gpt-image-1.5/edit` | Default for CUSTOM_PROMPT |
| FLUX 2 Pro Edit | `fal-ai/flux-2-pro/edit` | Multi-ref |
| FLUX Kontext | `fal-ai/flux-pro/kontext` | Default for gemstone/background/luxury |
| FLUX Kontext Max | `fal-ai/flux-pro/kontext/max` | Higher quality Kontext |
| FLUX 1.1 Redux | `fal-ai/flux-pro/v1.1/redux` | Style transfer |
| Recraft V3 I2I | `fal-ai/recraft/v3/image-to-image` | 1000 char prompt limit |
| Seedream 4.5 Edit | `fal-ai/bytedance/seedream/v4.5/edit` | Multi-ref |
| FLUX 1.1 Pro Ultra Redux | `fal-ai/flux-pro/v1.1-ultra/redux` | High-res catalog |
| Bria FIBO Edit | `bria/fibo-edit/edit` | Structured edit |
| FLUX 2 Klein 9B Edit | `fal-ai/flux-2/klein/9b/edit` | Fast multi-ref |

### Styling (2 models)

| Display name | Endpoint ID |
|--------------|-------------|
| Ideogram V3 Remix | `fal-ai/ideogram/v3/remix` |
| Grok Imagine Edit | `xai/grok-imagine-image/edit` |

### Virtual try-on (6 models — JEWELRY_ON_MODEL, CUSTOMER_TRY_ON only)

| Display name | Endpoint ID | Default for |
|--------------|-------------|-------------|
| FASHN Try-On v1.6 | `fal-ai/fashn/tryon/v1.6` | JEWELRY_ON_MODEL |
| Virtual Try-On (image-apps-v2) | `fal-ai/image-apps-v2/virtual-try-on` | CUSTOMER_TRY_ON |
| FLUX 2 LoRA Virtual Try-On | `fal-ai/flux-2-lora-gallery/virtual-tryon` | — |
| Kling Kolors VTON v1.5 | `fal-ai/kling/v1-5/kolors-virtual-try-on` | — |
| Cat-VTON | `fal-ai/cat-vton` | — |
| Leffa Virtual Try-On | `fal-ai/leffa/virtual-tryon` | — |

Catalog is seeded from `backend/seeds/fal_models_data.py` on API startup. Stale endpoints (e.g. removed Gemini slug) are deactivated automatically.

---

## 10. Key files (developer reference)

| File | Role |
|------|------|
| `backend/app/pipeline/composer.py` | Orchestrates master + multi-subject + variant |
| `backend/app/pipeline/layers.py` | Layer walk, Jinja render, token budget |
| `backend/app/pipeline/validator.py` | Job validation, `parse_jewelry_types()` |
| `backend/app/providers/prompt_augment.py` | Multi-image hint suffixes |
| `backend/app/providers/adapters/fal.py` | Prompt truncate, image field mapping, fal call |
| `backend/app/tasks/generate.py` | Job worker: compose → augment → route |
| `backend/seeds/prompt_txt_parser.py` | TXT → dynamic layers parser |
| `backend/seeds/prompt_txt_import.py` | One-time DB migration from TXT |
| `backend/seeds/migrate_prompt_txt.py` | CLI: `py -m seeds.migrate_prompt_txt` |
| `backend/seeds/prompts_data.py` | Workflow/type metadata |
| `backend/seeds/fal_models_data.py` | Model catalog + `image_field` config |
| `frontend/src/components/PromptEditor.tsx` | Admin layer UI |
| `frontend/src/components/studio/ModelSelector.tsx` | Workflow-filtered model dropdown + params |
| `frontend/src/components/studio/DynamicParamForm.tsx` | Schema-driven model parameters |
| `frontend/src/pages/StudioPage.tsx` | Job payload + multi-select jewelry types |

---

## 11. Mental model checklist

**For prompt authors (Admin):**

- Edit **master** for workflow rules; edit **subject** per jewelry type for anatomy/placement
- Use `insert_point` on master so subjects appear in the right place
- Use `{{ jewelry_type }}` in templates — it adapts for single or multi-select
- Preview with **Server preview** after changes
- Watch word count — long masters + multi-type subjects may hit token budget or model limits (Recraft 1000 chars)

**For operators (Studio):**

- Pick all jewelry types visible in the photo
- Upload reference portrait for try-on / style match workflows
- Choose AI model appropriate to workflow (VTON models only appear for try-on workflows)
- Additional instruction goes to `prompt_text` → user_insert layer or trailing append

**For debugging failed jobs:**

- Check Admin → Quality → error message (schema vs prompt length vs image load)
- Inspect job `provider_metadata.promptDebug` for composed layer trace
- Confirm active master/subject versions in Admin → Prompts
- Re-seed models if `image_url` vs `image_urls` mismatch errors appear

---

## 12. Example: Catalog Image with Ring + Bracelet

**Studio input:**

- Workflow: `CATALOG_IMAGE`
- Jewelry types: `Ring`, `Bracelet`
- Background variant: `Cream Velvet`
- Product image uploaded

**Compose result (conceptual):**

```
[Master: system role]
[Master: camera settings]
[Subject Ring: core description with jewelry_type=Ring]
[Subject Ring: placement rules]
[Subject Bracelet: core description with jewelry_type=Bracelet]
[Subject Bracelet: physics]
[Master: environment]
[Master: lighting]
[Master: preservation lock]
[Variant: Cream Velvet surface description]
[Optional user instruction]
```

**Negative (separate):** master AVOID layer + variant negative

**fal.ai call:**

```json
{
  "prompt": "<full composed + augmented text>",
  "image_urls": ["https://v3b.fal.media/files/.../product.jpg"],
  "resolution": "2K",
  "aspect_ratio": "1:1",
  "output_format": "png"
}
```

---

*Last updated: FAL-only catalog, model-driven Studio parameters, mandatory login, layer-based compose.*
