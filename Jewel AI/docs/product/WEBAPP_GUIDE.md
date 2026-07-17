# Jewel AI Studio — Web App Guide

## Stack

- **Frontend:** React 19 + Vite + TanStack Query (`New Project/web`)
- **Backend:** FastAPI + SQLAlchemy (`New Project/api`)
- **Image generation:** [fal.ai](https://fal.ai) only — **21 image-guided models** (14 ranked image-edit + 7 virtual try-on)

**Default workflow model:** Nano Banana Pro (`fal-ai/nano-banana-pro/edit`) — rank #1 in the Studio dropdown.

## Production (Railway)

- **App:** https://jewel-ai.up.railway.app/login
- **Health:** https://jewel-ai.up.railway.app/health

Set these in Railway service variables:

| Variable | Value |
|----------|-------|
| `API_PUBLIC_URL` | `https://jewel-ai.up.railway.app` |
| `FRONTEND_ORIGIN` | `https://jewel-ai.up.railway.app` |
| `NODE_ENV` | `production` |

`RAILWAY_PUBLIC_DOMAIN` is auto-detected when unset; explicit values above are recommended for fal webhooks and CORS.

## Quick start

1. Set `FAL_KEY` in `backend/.env` (get key from [fal.ai dashboard](https://fal.ai/dashboard/keys))
2. Run `RUN.bat` from repo root (or `scripts/dev-local.bat`)
3. Login (required for Studio and History):
   - **Admin:** `admin@jewelai.com` / `changeme`
   - **Studio user:** `studio@jewelai.com` / `studio123`
4. Open Studio at http://localhost:5173

## Environment variables

| Variable | Purpose |
|----------|---------|
| `FAL_KEY` | fal.ai API key (required for generation) |
| `API_PUBLIC_URL` | Public URL of API for local image uploads (default `http://localhost:8000`) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Seed admin user |
| `DEFAULT_USER_EMAIL` / `DEFAULT_USER_PASSWORD` | Seed studio user (role: `user`) |
| `ALLOW_PROMPT_RESEED` | When `true`, TXT files re-import on startup if hash changed. Default: enabled in `development` only |
| `JWT_SECRET` | Auth signing secret |

## Model selection (Studio)

All workflows require **uploading a product image**. Generation is always **text + image → image**.

The **AI Model** dropdown loads from `GET /api/models?image_edit_only=true&has_input=&image_count=`. Models are filtered by workflow, whether images are uploaded, and image count (VTON models require product + portrait).

### Image-edit models (14, ranked)

| Rank | Model | Endpoint |
|------|-------|----------|
| 1 | Nano Banana Pro Edit | `fal-ai/nano-banana-pro/edit` |
| 2 | FLUX 2 Max Edit | `fal-ai/flux-2-max/edit` |
| 3 | GPT Image 2 Edit | `openai/gpt-image-2/edit` |
| 4 | FLUX 2 Pro Edit | `fal-ai/flux-2-pro/edit` |
| 5 | FLUX Kontext | `fal-ai/flux-pro/kontext` |
| 6 | Nano Banana 2 Edit | `fal-ai/nano-banana-2/edit` |
| 7 | Seedream 5 Lite Edit | `fal-ai/bytedance/seedream/v5/lite/edit` |
| 8 | Seedream 4.5 Edit | `fal-ai/bytedance/seedream/v4.5/edit` |
| 9 | GPT Image 1.5 Edit | `fal-ai/gpt-image-1.5/edit` |
| 10 | FLUX 2 Dev Edit | `fal-ai/flux-2/dev/edit` |
| 11 | GLM-Image I2I | `fal-ai/glm-image/image-to-image` |
| 12 | FireRed Image Edit | `fal-ai/firered-image-edit-v1.1` |
| 13 | Grok Imagine Edit | `xai/grok-imagine-image/edit` |
| 14 | FLUX Dev I2I | `fal-ai/flux/dev/image-to-image` |

### Virtual try-on models (7)

| Model | Endpoint | Inputs |
|-------|----------|--------|
| FASHN Try-On v1.6 | `fal-ai/fashn/tryon/v1.6` | `model_image` + `garment_image` |
| Virtual Try-On (image-apps-v2) | `fal-ai/image-apps-v2/virtual-try-on` | `person_image_url` + `clothing_image_url` |
| FLUX 2 LoRA Virtual Try-On | `fal-ai/flux-2-lora-gallery/virtual-tryon` | `image_urls[]` (person, product) |
| Kling Kolors VTON v1.5 | `fal-ai/kling/v1-5/kolors-virtual-try-on` | `human_image_url` + `garment_image_url` |
| Cat-VTON | `fal-ai/cat-vton` | `human_image_url` + `garment_image_url` |
| Leffa Virtual Try-On | `fal-ai/leffa/virtual-tryon` | `human_image_url` + `garment_image_url` |
| Decart Lucy2 VTON | `decart/lucy2-vton/realtime` | try-on fields per model config |

**Excluded:** text-only models, upscale-only endpoints, and inpainting models that require a mask (e.g. `ideogram/v3/edit`).

Each model stores a `config.image_field` (or `config.try_on_fields`) in the DB. The Fal adapter maps product + reference images to the correct schema automatically. Recraft prompts are truncated to 1000 characters before the API call.

Each model exposes dynamic parameters (resolution, guidance scale, remix strength, etc.) from its fal API schema. Preferences are saved per workflow in browser `localStorage`.

## Roles and access

| Role | Studio / History | Admin page | Prompt editing |
|------|------------------|------------|----------------|
| `user` | Yes | Hidden | No |
| `admin` | Yes | Full access | Yes |

All API routes for jobs, uploads, and config require login. Prompt, provider, and user management routes require `admin`.

Change passwords in **Admin → Users** (admin can reset any user; everyone can update their own account).

## Admin

| Tab | Purpose |
|-----|---------|
| fal.ai | Configure `FAL_KEY` |
| Models | Enable/disable models, edit default parameters |
| Prompts | DB-only master/subject layer editor — add, edit, reorder, delete layers |
| Sandbox | Compose prompt + live test generation |
| Users | Create studio users, reset passwords, update admin account |

## Prompt pipeline (DB-only layers)

**No hardcoded prompt text** in the codebase. All master and subject (child) layers are stored in the database and edited in Admin → Prompts.

- **Master** — one per workflow; optional `subject_insert` layer pulls in the child prompt
- **Subject (child)** — one per **workflow + jewelry type** (`CATALOG_IMAGE` + `Ring`, `CUSTOMER_TRY_ON` + `Ring`, …)
- **Variants** — optional per-workflow text (create in Prompt Editor)

The frontend never builds prompt strings — only `composer.py` assembles from DB layers.

### Layer types

| type | Behavior |
|------|----------|
| `text` | Jinja-rendered, joined into body |
| `insert_point` | Inserts subject layers for the job's `jewelry_type` |
| `negative` | Sent as `negative_prompt` — not in body |
| `variant_insert` / `user_insert` | Optional insertion markers |

### Composition modes

- **Layered (default):** iterate layers by `order`, render, join.
- **Raw:** `raw_override` is the body; `negative` type layers still apply separately.

### Jinja variables (job fields)

`{{ jewelry_type }}`, `{{ metal_type }}`, `{{ gemstone_target_color }}`, `{{ background_style }}`, `{{ lighting_style }}`, `{{ prompt_text }}`, `{{ workflow }}`

### First-time setup

On API start, empty master/subject shells are created if missing. **Prompt text is not loaded from `.txt` files on startup.** Run the one-time migration to seed from `data/seed-prompt-templates/*.txt`:

```bash
cd backend
py -m seeds.migrate_prompt_txt
```

To re-seed from files (creates new versions), use `--force`:

```bash
py -m seeds.migrate_prompt_txt --force
```

After migration, the database is the sole source of truth. Edit prompts in **Admin → Prompts**.


## API endpoints

- `GET /api/models` — image-edit model catalog for Studio (`image_edit_only=true` by default)
- `POST /api/jobs` — `{ model_endpoint_id, model_params, asset_id, ... }`
- `GET /api/config/workflow-fields` — variant field mapping
- `POST /api/prompts/test/generate` — admin sandbox generation

## Troubleshooting

### Job stays on "Processing" forever

- If **Redis is running but no Celery worker** is started, jobs were previously stuck in `PENDING`. This is fixed: the API now processes jobs in a background thread unless a Celery worker is actually connected.
- Restart the API after updating (`RUN.bat`).

### fal.ai errors

- Set `FAL_KEY` in `api/.env` **or** Admin → fal.ai tab.
- Upload a product image before generating — all models require an input image.
- Image field mapping is per-model (`image_url` vs `image_urls`) from the model catalog config, not inferred from the endpoint path.
- Local images are uploaded to fal CDN before inference (`fal_client.upload_file`).

### No models in dropdown

- Restart API to run seeds. Check Admin → Models tab that models are enabled.
