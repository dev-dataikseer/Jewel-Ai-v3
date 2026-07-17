# Product Requirements Document
## Jewel V3 — React + Python Rebuild
### Prompt Pipeline Engine & Multi-Provider Image Generation Platform

**Status:** Draft for architecture review
**Supersedes:** Current Express/Next.js/SQLite production app (Grade C/D across most subsystems per codebase audit)
**Scope note:** Deployment/hosting decisions are explicitly out of scope for this document — covered separately.

---

## 1. Executive Summary

The current app is a working single-operator MVP, but the audit is blunt about why it can't scale: six overlapping sources of truth for prompts, admin edits silently wiped on every server restart, workflow-specific parameters (gemstone color, metal type, background style) collected from the UI and then dropped before they reach the AI, an in-memory job queue that loses everything on restart, unbounded parallel API calls on bulk jobs, no authentication anywhere including the admin panel, and plaintext API keys.

None of that is a "this framework is wrong" problem — it's an architecture problem. The rebuild keeps every real feature your users rely on (the 9 workflows, the admin panel, history, rate tools, favorites, regenerate, bulk generation) but replaces the two systems that were actually broken: prompt composition becomes a proper versioned pipeline engine instead of a JSON blob assembled from six conflicting sources, and image generation becomes a fal.ai-only model router backed by per-endpoint schemas.

Stack: **React (Vite) + TypeScript** frontend, **Python + FastAPI** backend. Deployment is deferred — this document only defines what gets built.

---

## 2. Goals

Fix every Critical/High item from the audit by construction, not by patching: prompts must be DB-first and never reverted by a server restart; every workflow parameter the UI collects must be persisted and must reach the assembled prompt; the queue must survive a restart and must enforce concurrency limits; every admin and internal route must require authentication; API keys must be encrypted at rest; bulk jobs of 30 images must not fire 30 simultaneous provider calls.

Add the capability that was entirely missing: a true multi-provider, multi-model generation layer (cloud APIs plus self-hosted/local models) with automatic fallback, instead of one provider with no alternative when it fails or rate-limits.

Make the prompt system genuinely "complex pipeline" capable — composable, versioned, testable in a real sandbox — instead of a single template field per workflow with a free-text bar bolted on.

---

## 3. Technology Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | React 19 + TypeScript + Vite | No Next.js — there's no server-rendering need once Python owns the API; Vite gives a faster, simpler build |
| Frontend styling | Tailwind CSS + shadcn/ui | Matches existing UI patterns (Button, Card, Dialog, Tabs, etc.) already in use |
| Frontend state/data | TanStack Query (React Query) | Replaces raw Axios polling — handles caching, retries, and real-time job status cleanly |
| Backend framework | Python 3.12 + FastAPI | Async-native, Pydantic validation for complex nested prompt-pipeline payloads, auto-generated OpenAPI docs |
| ORM | SQLAlchemy 2.0 + Alembic (migrations) | Alembic replaces the current "no migrations, just `db push`" approach — explicit, reviewable schema changes |
| Database | PostgreSQL | Replaces SQLite — required for write concurrency once the job queue runs multiple workers in parallel |
| Job queue | Celery + Redis (or `arq` if a lighter footprint is preferred) | Replaces the in-memory `setImmediate` queue — survives restarts, supports retries, concurrency limits, and scheduled sweepers for stuck jobs |
| Real-time job status | Server-Sent Events (SSE) or WebSocket via FastAPI | Replaces the 2.5s polling loop — push status changes instead of every client polling every job |
| File/image storage | S3-compatible object storage (e.g. Cloudflare R2) | Replaces local `backend/uploads/` — required for multi-instance scaling and signed-URL access control |
| Local model runtime | ComfyUI (primary) + Automatic1111 (secondary) | Reached over HTTP/websocket from a Celery worker, treated as just another provider |
| Auth | FastAPI + JWT (e.g. `fastapi-users` or custom) | Replaces "no authentication on any route" — covers admin, and activates the unused `User`/`Team` schema |
| Secrets | Encrypted at rest (e.g. Fernet/KMS-backed) for provider API keys | Replaces plaintext `encryptedApiKey` field that wasn't actually encrypted |

---

## 4. Feature Inventory (Carried Forward, Fixed)

These are the features your current app already has and that the rebuild preserves end to end. Only the *implementation* changes — every item below gets a working, persisted, end-to-end path from UI to prompt to provider, which is explicitly what's broken today.

### 4.1 Generation Workflows

Catalog Image (studio product shot, supports bulk), Jewelry On Model (requires jewelry + portrait reference image), Gemstone Color Change (target color selection actually reaches the prompt), Customer Try-On (jewelry + customer photo), Background Replacement (style selector — marble, velvet, silk, lifestyle — actually reaches the prompt), Luxury Enhancement (metal type selector — yellow gold, rose gold, platinum — actually reaches the prompt), Custom Prompt (full free-text control), Bulk Generation (up to 30 images, runs as a true batch with per-asset jobs, controlled concurrency instead of unbounded parallel calls), Rate Tools (non-AI: live metals spot pricing).

### 4.2 Jewelry Types

Ring, Necklace, Bangles, Bracelet, Earrings (Studs / Drops / Hoops), Pendant, Watch, Brooch, Anklet, Cufflinks, and Multiple Items (treated as a unified set with consistent lighting/shadow across all detected pieces).

### 4.3 Studio Parameters (per generation)

Aspect ratio selection (1:1, 16:9, 9:16, 3:4, 4:3), fal.ai model selection with schema-driven parameters, person-generation policy for model/try-on workflows, number of images per job, custom free-text instruction appended to the assembled pipeline, multi-select jewelry type with "Multiple Items" handling.

### 4.4 Job & Asset Management

Drag-and-drop upload (JPG/PNG/WEBP), live job status pushed to the client (not polled), download/favorite/regenerate actions, working deep-link to a specific job by ID, recent-jobs strip, full history gallery with pagination, regenerate that actually carries forward all original workflow parameters (current app loses this metadata on regenerate).

### 4.5 Admin Panel

Overview (live job/asset/batch/favorite counts, success rate — now backed by real per-job provider/version data instead of static counters), Provider Settings (FAL_KEY credential management and fal.ai health test), Prompts & Pipeline Builder (replaces "Prompts & Subjects" — see Section 5), Prompt Test Sandbox (real preview: assembled prompt text + live fal.ai test generation, not just a JSON preview), Spot Rates (manual gold/diamond rate entries — unchanged), Quality Control (failure list, diagnostics, structured log viewer — now with auth).

### 4.6 Features That Exist Only as Unused Schema Today (Now Actually Implemented)

User accounts with role-based access (admin / operator / viewer), team/white-label support, public share links for completed jobs (with expiry), credit ledger that actually deducts on job completion instead of a hardcoded value, Style Presets that are actually fetched in the UI and actually appended to the composed prompt, and a `PromptVariant` system so workflow-specific dropdowns (gemstone color, background style, metal type) are admin-manageable instead of hardcoded string-matching against the jewelry type field.

---

## 5. Core System 1 — Prompt Pipeline Engine

This directly replaces the audited "6 overlapping sources of truth" architecture (`prompts.ts` code defaults, a `PromptTemplate` DB table that gets wiped on every restart, a half-used `SubjectPrompt` table, a destructive seed function, duplicated admin UI defaults, and a reference-only JSON doc nothing actually reads).

### 5.1 Design principles

**Single source of truth, DB-first.** Code-level defaults exist only as a one-time seed (create-if-not-exists), never as a runtime fallback that silently overrides admin edits. **Composable, not monolithic.** A prompt is assembled from independently versioned, reusable layers rather than one long template string per workflow. **Plain text to fal.ai, always.** The composer's only output type is a plain string plus a debug trace, never a JSON blob.

### 5.2 Pipeline layers

1. **Master Template** — per workflow: system role, camera/technical settings, environment, lighting and physics rules, preservation lock (what must never change — jewelry geometry, gemstone cut), negative prompt.
2. **Subject Definition** — per jewelry type: full structured description (not just one field — the existing schema has four fields and only uses one), so material, form, and interaction-with-body details are all available to the composer.
3. **Prompt Variant** — the per-workflow dropdown options (target gemstone color, background style, metal type) stored as real rows the admin can add/edit/reorder, explicitly keyed to job fields — not pattern-matched against a jewelry-type string, which is the root cause of the current "UI sends 'Ring', composer expects 'ruby'" bug.
4. **Style Preset** — optional named add-on block, fetched by the frontend and actually appended during composition (currently dead end-to-end).
5. **User Instruction** — the free-text custom prompt bar, appended last so it can refine but not override the structural layers.
6. **Negative Prompt Assembly** — universal negative prompt plus workflow-specific exclusions, actually used (currently imported and unused).

### 5.3 Composition formula

```
FINAL PROMPT (plain text) =
  Master.systemRole + Master.cameraSettings + Master.environment
  + Subject.description (mapped to selected jewelry type)
  + Variant.text (mapped explicitly from job.gemstoneTargetColor /
                   job.backgroundStyle / job.metalType — never string-matched)
  + StylePreset.promptAddon (if selected)
  + Master.lightingAndPhysics + Master.preservationLock
  + UserInstruction (free text, optional)
  + "Avoid and exclude: " + Master.negativePrompt + Variant.negativeAddon
```

### 5.4 Versioning and testing

Every edit to a Master Template, Subject Definition, or Prompt Variant creates a new version row rather than overwriting in place, so a regression can be rolled back instantly and every `GenerationJob` can record exactly which version of each layer produced it. The **Prompt Test Sandbox** in admin runs the full composer against a real sample image and a chosen provider, showing the exact assembled text the provider will receive — not a JSON approximation — before anything goes to production. `isActive` flags are respected by the composer (currently a known bug: disabled templates still apply).

---

## 6. Core System 2 — Multi-Provider Generation Layer

This replaces the old single-model setup with a fal.ai-only router that selects among image-plus-text endpoints by workflow and model capability.

### 6.1 Provider interface

Every provider — cloud or local — implements the same contract, so the router and the rest of the app never branch on which one is active:

```python
class ImageGenProvider(Protocol):
    async def generate(self, request: GenerationRequest) -> GenerationResult: ...
    async def health_check(self) -> ProviderStatus: ...
    def estimate_cost(self, request: GenerationRequest) -> float: ...
    capabilities: ModelCapabilities  # max resolution, supports inpainting,
                                       # supports multi-image input, supports
                                       # person generation, text-to-image only, etc.
```

### 6.2 Supported providers at launch

**Cloud:** fal.ai image editing and virtual try-on endpoints only, with each endpoint represented by a model definition containing capabilities, input schema, default parameters, and field mapping.

**Local/self-hosted:** ComfyUI (primary — node-based workflows are a strong fit for multi-step jobs like inpaint + upscale + color correction in one pass) and Automatic1111 (secondary), both reached via their HTTP APIs from a Celery worker. This is the part that was entirely absent from the current app and is explicitly requested: local models are first-class providers, not an afterthought, useful for cost control on bulk jobs and for keeping client jewelry images fully on infrastructure you control.

### 6.3 Generation Router

Sits between the Prompt Pipeline Engine and fal.ai. Responsibilities: per-workflow default endpoints, capability-aware filtering (multi-image input, virtual try-on, material accuracy), circuit breaker handling for fal.ai health, and optional cost-aware routing between seeded fal.ai endpoints.

### 6.4 Job execution and concurrency

Celery workers pull from the queue with an explicit concurrency limit (the audit flags *unbounded* parallel calls on a 30-image bulk batch as a critical bug — this is a hard cap, configurable per provider, e.g. 2–3 concurrent calls to a single rate-limited API at once). A startup sweeper requeues or fails jobs stuck in `PROCESSING` from a previous crash (current app leaves these stuck forever). `providerMetadata` (model used, aspect ratio, cost) is merged on completion, never overwritten (audited bug: currently destructive).

---

## 7. Data Model (conceptual, SQLAlchemy/Postgres)

Carries forward every entity the current Prisma schema already defines correctly, fixes the ones flagged as drifted, and activates the ones that exist as schema only.

`User` / `Team` — now wired to real auth and role-based access (admin / operator / viewer), supporting white-label team settings. `CreditLedger` — now actually deducts on job completion instead of recording a hardcoded value. `ShareLink` — now has a real API for generating expiring public links to a completed job. `Project` / `Batch` / `Asset` / `GenerationJob` — same purpose as today's `Project`/`Batch`/`Asset`/`Job`, with the `Batch.name` field bug fixed at the schema level and `GenerationJob` storing full lineage (master template version, subject version, variant version, style preset, provider used, model used, cost, retries, error detail) rather than the current minimal status/output fields. `PromptMasterTemplate` / `PromptSubject` / `PromptVariant` / `StylePreset` — the versioned pipeline layers from Section 5, replacing the current `PromptTemplate`/`SubjectPrompt` pair and adding the missing `PromptVariant` concept. `Provider` — replaces `ProviderSetting`: supports multiple rows (one per cloud or local provider), encrypted credentials, priority/fallback order, capability flags, live health status. `RateEntry` / `Favorite` — unchanged in purpose.

---

## 8. API Design (FastAPI)

Routers mirror the current REST surface where it already works well, with auth added everywhere and the prompt/provider endpoints redesigned around the new systems:

`/api/assets` — upload (single + bulk), now writing to object storage instead of local disk. `/api/jobs` — create, get by ID (proper 404 on missing job, fixing the current 200+null bug), list with cursor pagination (current app is unpaginated and will blow up memory on large history), regenerate (now correctly carries forward all original parameters). `/api/jobs/stream` — SSE/WebSocket endpoint for live status, replacing 2.5s client-side polling entirely. `/api/projects` — list/get, paginated. `/api/pipelines/{workflow}/assemble` — returns the fully assembled plain-text prompt for a given set of selections, without generating — this is what powers a real Prompt Test sandbox. `/api/prompts/templates`, `/api/prompts/subjects`, `/api/prompts/variants`, `/api/prompts/presets` — full versioned CRUD, admin-only. `/api/providers` — CRUD for provider configs (admin-only, credentials never returned in responses), `/api/providers/health` — live status per provider, powering a real engine-health metric instead of a static dashboard number. `/api/rates` — live + manual, unchanged in purpose. `/api/favorites`, `/api/share-links`, `/api/credits` — new, backed by the previously-unused schema. `/api/admin/metrics`, `/api/admin/logs` — admin-only, structured logs instead of raw file reads.

---

## 9. Security

Every route under `/api/admin/*`, `/api/providers/*`, `/api/prompts/*` (write operations), and `/api/admin/logs` requires authentication — the current app has none of this, including on the admin panel itself. Provider API keys are encrypted at rest (Fernet or a managed KMS), never returned in any API response, and never reach the frontend bundle. Uploaded and generated images are served via signed, expiring URLs from object storage rather than a public `/uploads/*` path. CORS is restricted to the known frontend origin instead of wide open. Request payloads are validated and whitelisted at the Pydantic model level — no mass-assignment of arbitrary job fields, which the audit flags as a current risk. Diagnostics endpoints (current `/api/diagnose` exposes key fragments publicly) are admin-only and never expose credential material, even partially.

---

## 10. Scalability

PostgreSQL plus a real job queue removes the two hardest current ceilings (SQLite write contention and an in-memory queue that can't run more than one process). Object storage removes the local-disk dependency that breaks multi-instance deployment. SSE/WebSocket for job status removes N-clients-polling-every-2.5-seconds load. Cursor pagination on jobs/projects removes the unpaginated-history memory risk. Celery worker concurrency is independently scalable from the API process — more workers means more parallel generation throughput without touching the web tier.

---

## 11. Phased Build Plan (excluding deployment)

**Phase 1 — Foundation:** Postgres schema + Alembic migrations covering every entity in Section 7 (including the previously-unused ones), FastAPI project skeleton with auth, fal.ai adapter, and seeded image-plus-text model catalog.

**Phase 2 — Prompt Pipeline Engine:** Master Template / Subject / Variant / Style Preset models and versioning, the composer producing plain text only, the Prompt Test sandbox, migration of all 9 existing workflows onto pipeline configuration instead of hardcoded prompt strings.

**Phase 3 — Generation Router & Queue:** Celery + Redis, concurrency limits, circuit breaker/health checks, second cloud provider adapter, job lineage recording.

**Phase 4 — Local Model Integration:** ComfyUI adapter, Automatic1111 adapter, fallback chains that include local providers.

**Phase 5 — Frontend Rebuild:** React + Vite app covering Studio, Admin (six tabs, now fully wired and authenticated), History, with TanStack Query + SSE replacing the current polling pattern, all previously-broken UI-to-backend wiring (workflow parameter dropdowns, style preset selector, deep links, regenerate metadata) fixed by construction.

**Phase 6 — Schema-Backed Features:** real auth/roles, team white-labeling, share links, credit ledger enforcement.

**Phase 7 — Hardening:** test coverage, structured logging/observability, admin diagnostics UI for the existing health-check endpoints.
