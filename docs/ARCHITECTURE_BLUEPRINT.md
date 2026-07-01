# Jewel V3 Architecture Blueprint

## Source Codebase Findings

### Old Project

- Node/Express backend with Prisma models, uploads, queueing, admin prompt editing, workflow list, rates, favorites, history, and early single-provider image generation.
- Next.js frontend with Studio, Admin, and History pages plus shadcn-style UI primitives.
- Main gaps identified in its own audit: no real auth/RBAC, prompt sources overwritten on restart, dropped workflow parameters, weak provider metadata handling, unbounded generation concurrency, and monolithic pages.

### New Project

- FastAPI backend, React/Vite frontend, docs, prompt text library, tests, Celery/Redis hooks, RBAC, SSE job streaming, fal.ai provider routing, and DB-backed prompt layers.
- Stronger prompt pipeline: master, subject, variant, and style-preset composition with validation and negative prompt separation.
- Better production direction: Alembic migrations, seed scripts, provider registry, model definitions, user management, metrics, and prompt sandbox.

## Jewel V3 Consolidation

`Jewel_V3` uses the newer FastAPI/Vite implementation as the running baseline and preserves the older app's feature coverage:

- Studio workflows: catalog image, jewelry-on-model, gemstone color change, customer try-on, reference style match, background replacement, luxury enhancement, custom prompt, bulk generation, and rate tools.
- Admin workflows: user management, provider/model settings, prompt template studio, prompt sandbox, metrics, and role-gated admin routes.
- Generation workflow: asset upload, structured jewelry metadata, prompt composition, fal.ai execution, Celery dispatch, Redis-backed scaling, SSE job state updates, history, favorites, regenerate, and share links.

## Backend Layers

- `app/domain`: jewelry business concepts such as generation intent, strength tiers, and category language.
- `app/application`: use-case facades. Current prompt composition is exposed through `JewelryPromptComposer`.
- `app/infrastructure`: provider, storage, database, and queue adapters. fal.ai is exposed through `FalImageProvider`.
- `app/presentation`: transport layer entry points. REST routers remain under `app/api/routers` and are mounted by `app.main`.
- `app/prompt_engine`: stable import surface over the DB-backed matrix prompt composer.

The existing route modules are intentionally preserved to keep the app runnable while v3 boundaries are introduced.

## Jewel Prompt Engine

The prompt engine composes:

```text
Final Prompt = Master Workflow Layer + Jewelry Subject Layer + Variant/Style Layer + Model Workflow Constraints
```

Core safeguards:

- Positive material language for VVS clarity, micro-pave prongs, die-struck metal, polished 18k metal, and laser-sharp facets.
- Negative prompt separation for deformed prongs, asymmetrical settings, blurred facets, melted metal, low-contrast shadows, soft edges, stock-photo artifacts, and double shanks.
- Jinja validation blocks unresolved template variables before provider calls.
- Token budgeting drops optional layers before critical preservation constraints.

Strength tier policy:

- `0.1-0.3`: high preservation for cleaning, glare reduction, and color correction.
- `0.4-0.6`: controlled re-contextualization for luxury backgrounds and studio reflections.
- `0.7-0.9`: creative transformation for try-on and editorial scenes.

## Deployment

- `config/docker-compose.yml`: PostgreSQL, Redis, API, Celery worker, and frontend.
- `config/backend.Dockerfile`: FastAPI service image.
- `config/frontend.Dockerfile`: Vite build served by Nginx.
- `config/.env.production.example`: required production environment values.

## Next Hardening Steps

- Move SQLAlchemy access to async sessions with `asyncpg` if full async database I/O is required.
- Add OAuth provider integrations beyond JWT email/password login.
- Add object storage defaults for R2/S3 and CDN-backed asset URLs.
- Split large Studio/Admin React pages into smaller workflow-specific panels.
- Add Playwright coverage for upload, prompt preview, generation, admin edit, and history deep-link flows.
