# Backup & rollback runbook (Jewel AI V4)

## Railway Postgres

1. **Snapshots:** Railway → Postgres service → Backups / Snapshots. Enable daily snapshots before prod traffic.
2. **Pre-deploy dump (optional):**
   ```bash
   railway connect Postgres
   # or: pg_dump "$DATABASE_URL" -Fc -f jewel_$(date +%Y%m%d).dump
   ```
3. **Restore:** create a new Postgres from snapshot, update `DATABASE_URL`, redeploy API + worker.

## Object storage (R2 / Railway Bucket)

- Keep versioning or a retention policy (≥30 days) on generated outputs.
- Inputs under `uploads/` are durable only if `STORAGE_BACKEND=r2` (local disk is ephemeral on Railway).

## App image rollback

1. Railway → Deployments → select previous successful deploy → **Redeploy**.
2. If schema migration was forward-only and incompatible:
   - Restore DB snapshot from before the bad deploy, **then** redeploy the previous image.
   - Prefer additive Alembic migrations; avoid destructive `downgrade` in prod unless rehearsed.

## Worker / beat

- Worker image runs Celery **worker + beat**. If credits or stuck-job sweep stop, check worker logs and beat schedule.
- After rollback, confirm `/ready` returns 200 and a test generation completes.

## Verification after restore

1. `GET /ready` → database + redis true  
2. Login + generate one catalog image  
3. Cancel an in-flight job (status CANCELLED)  
4. Admin → fal credits (requires `FAL_ADMIN_KEY`)
