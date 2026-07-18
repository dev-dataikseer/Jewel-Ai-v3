# Deploy layout (Jewel AI V4)

## Git vs Railway root

Application sources live under **`Jewel AI/`** (`backend/`, `frontend/`, `deploy/`).

Railway looks for **`railway.toml` at the git repository root**. That file (and root
`Dockerfile` / `Dockerfile.worker`) copy sources from `Jewel AI/…`.

| Setting | Value |
|---------|-------|
| **Root Directory** | *(leave empty)* — do **not** set to `Jewel AI` |
| API config | `railway.toml` → `Dockerfile` |
| Worker config | `railway.worker.toml` → `Dockerfile.worker` |

If Root Directory is mistakenly set to `Jewel AI`, either clear it or point the
service config at the nested `Jewel AI/railway.toml` instead.

## Local compose (mirrors Railway)

```bash
cd "Jewel AI/deploy/docker"
docker compose up --build
```

- **api**: `alembic upgrade head` then uvicorn; `SCHEMA_VIA_ALEMBIC=true`
- **worker**: Celery worker **with beat** (stuck-job sweep + fal credits refresh)
- Images install from `backend/requirements.lock.txt`

## App version

Production image / product line: **Jewel AI V4**.

Canonical Railway instructions: [`docs/deployment/RAILWAY_DEPLOY.md`](deployment/RAILWAY_DEPLOY.md)
(Root Directory empty — same as this file).
