# Prompt Profile V2 — Admin editing guide

## Mental model

Each workflow has **two pages**:

| Page | When it is used |
|------|-----------------|
| **Without reference** | Product image only |
| **With reference** | Any secondary image: style reference, portrait, or logo |

There are **no shared fragments** and **no `{{PLACEHOLDERS}}`**.

Prompt content is a JSON map: **heading → description**. At compose time this becomes:

```
ROLE: …

CAMERA: …
```

## Where to edit

Admin → **Prompts** opens **Prompt Studio** (one window):

1. Pick a workflow
2. Left navigator: Without / With reference, Jewelry types, Image roles, Presets, Advanced
3. Edit sections (add/remove headings)
4. Save new version
5. Live preview with simulated image checkboxes

## Image roles

Logo is **not** a branding matrix. It is an image slot labeled for the model:

> Image {index} is the company logo…

Same for product / theme / portrait.

## Enabling runtime V2

1. Run migration: `python scripts/migrate_to_prompt_profiles.py`
2. Set `PROMPT_PROFILE_V2=true` **or** leave unset — once profiles exist for a workflow, compose auto-uses V2 for that workflow
3. Alembic: `alembic upgrade head` (revision `008_prompt_profiles_v2`)

## Legacy path

Until profiles are migrated, jobs still use the old master/subject/fragment pipeline (`composePath: legacy_v1`).
