# Production Readiness Audit — Jewel AI V4

**Date:** 2026-07-17  
**Scope:** Pre-production blockers through ops polish (Phases 0–4)  
**App root:** `Jewel AI/` (Railway Root Directory)

## Summary

The app is feature-complete for soft launch after the fixes below. Critical schema, cancel/stuck-job, and webhook durability issues are addressed. Remaining Medium/Low items are deferred by design.

| Severity | Area | Evidence | Root cause | Impact | Fix | Status | Notes |
|----------|------|----------|------------|--------|-----|--------|--------|
| Critical | Schema / Alembic | `alembic/versions/001_initial.py` empty; `SCHEMA_VIA_ALEMBIC` skipped `create_all` | Baseline never created tables | Fresh prod DB has no tables | Real `001` via `Base.metadata.create_all`; Dockerfile/`compose` run `alembic upgrade head` | Fixed | Verified on empty SQLite |
| High | Job cancel | `jobs.py` `revoke(job_id)` | Job UUID ≠ Celery task id | Cancel does not stop worker | Persist `celery_task_id`; revoke that id | Fixed | Migration `004_celery_task_id` |
| High | Stuck jobs | `sweep_stuck_jobs` re-enqueues without lease | Concurrent sweeps double-run fal | Double billing | Redis `requeue-lease`; skip webhook_pending/accepted | Fixed | TTL 120s |
| High | Webhook durability | FastAPI `BackgroundTasks` in `providers.py` | Lost on API restart | Jobs stuck PROCESSING | Celery `finalize_fal_webhook` | Fixed | Thread fallback without worker |
| High | Deploy layout | Nested `Jewel AI/` vs flat git root | Wrong Railway root → empty deploy | Broken deploys | `docs/DEPLOY_LAYOUT.md`; compose worker+beat | Fixed | Set Railway Root = `Jewel AI` |
| High | fal credits UI | `Credits: Unavailable` with balance >$10 | Billing API needs **Admin** scope key; API key → 403 | Misleading ops signal | `FAL_ADMIN_KEY`; clearer errors; admin-only refresh | Fixed | User must set Admin key |
| Medium | Security headers | nginx/API lacked CSP/HSTS | Missing middleware | XSS/clickjacking risk | Middleware + nginx headers | Fixed | |
| Medium | Signed URL TTL | 24h default | Long-lived media URLs | Share leakage window | Default 2h via `MEDIA_SIGNED_URL_TTL_SECONDS` | Fixed | |
| Medium | Billing refresh authz | Any authenticated user could hit fal | Abuse / rate burn | Restrict POST refresh to admin | Fixed | GET cached remains open |
| Medium | OpenAPI in prod | `/docs` enabled | Surface area | Disable when `is_production` | Fixed | |
| Medium | ETA Redis | New connection per job list/stream | Latency under load | Shared Redis client | Fixed | |
| Medium | Stream token N+1 | Per-id ownership queries | Slow bulk stream tokens | Single `id IN (...)` query | Fixed | |
| Medium | DB pool | No `pool_recycle` | Stale Postgres connections | `pool_recycle=1800` | Fixed | |
| Medium | Health vs ready | `/health` mixed liveness + deps | Bad orchestration signals | `/health` liveness; `/ready` DB+Redis | Fixed | Railway uses `/ready` |
| Medium | Frontend bundle | Eager Admin/History/Rates | Large initial Studio load | `React.lazy` + vendor chunks | Fixed | |
| Medium | History UX | Eager images; no error retry | Poor gallery UX | `loading=lazy`, onError, error state, hidden-tab poll pause | Fixed | |
| Low | Rates/Admin loading | Silent failures / zero skeletons | Misleading UI | Loading/error/skeleton states | Fixed | |
| Medium | CI / lockfile | CI untracked; loose pins | Drift / unknown vulns | `.github/workflows/ci.yml`; `requirements.lock.txt`; audits | Fixed | Audits `continue-on-error` |
| Medium | Ops runbook | No backup/rollback doc | Slow incident response | `docs/ops/BACKUP_ROLLBACK.md` | Fixed | |
| Low | StudioPage rewrite | Large monolith page | Maintainability | Deferred | Deferred | Explicit out of scope |
| Low | httpOnly cookie auth | JWT in localStorage | XSS token theft | Shorten TTL + CSP interim | Deferred | Phase 4 follow-up |
| Low | CDN / thumbnails | Full-res gallery | Bandwidth | Deferred | Deferred | |
| Low | Full APM / tracing | Logs only | Harder prod debug | Sentry optional follow-up | Deferred | |
| Low | History virtualization | Grid for all items | Pain >~100 | Deferred | Deferred | |

## Verification checklist

1. Empty Postgres/SQLite: `alembic upgrade head` creates full schema; API with `SCHEMA_VIA_ALEMBIC=true` boots.
2. Cancel in-flight job: Celery revoke uses `celery_task_id`; status `CANCELLED`.
3. Stuck sweep: Redis lease prevents double enqueue.
4. Webhook: finalize runs as Celery task (or durable thread fallback locally).
5. Frontend: Admin/History/Rates are lazy chunks.
6. `/ready` fails when Redis or DB down; `/health` stays up.
7. CI: pytest + frontend build + alembic upgrade on empty DB.

## Required env for credits widget

```
FAL_KEY=<api-scope ok for generation>
FAL_ADMIN_KEY=<admin-scope required for /v1/account/billing>
```

Without `FAL_ADMIN_KEY`, the UI correctly shows Unavailable (fal returns 403 for API-scope keys).
