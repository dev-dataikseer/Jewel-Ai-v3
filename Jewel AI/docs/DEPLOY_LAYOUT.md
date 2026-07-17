# Deploy layout (Jewel AI V4)

## Git vs Railway root

The canonical application tree lives under **`Jewel AI/`** at the repository root
(`backend/`, `frontend/`, `deploy/`, `Dockerfile`, `railway.toml`).

In the Railway dashboard:

| Setting | Value |
|---------|-------|
| **Root Directory** | `Jewel AI` |
| API service Dockerfile | `Dockerfile` (monolith: API + SPA) |
| Worker service Dockerfile | `deploy/docker/Dockerfile.worker` (worker + beat) |
| Worker config | `railway.worker.toml` |

Do **not** point Railway at the parent folder that also contains `archive/` or
`Jewel AI - Copy/` — those are not the deployable app.

## Local compose (mirrors Railway)

```bash
cd "Jewel AI/deploy/docker"
docker compose up --build
```

- **api**: `alembic upgrade head` then uvicorn; `SCHEMA_VIA_ALEMBIC=true`
- **worker**: Celery worker **with beat** (stuck-job sweep + fal credits refresh)
- **web**: optional nginx front (local); Railway serves SPA from the API image

## App version

Production image / product line: **Jewel AI V4**.
