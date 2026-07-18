# Jewel AI V4 — Railway deployment

Deploy **Jewel AI V4** to [Railway](https://railway.app) and connect custom domain `hj-jewel-ai.data-ikseer.com`.

Repo: https://github.com/dev-dataikseer/Jewel-Ai-v3

## Git vs Railway root

Application sources live under **`Jewel AI/`** (`backend/`, `frontend/`, `deploy/`).

Railway looks for **`railway.toml` at the git repository root**. That file (and root
`Dockerfile` / `Dockerfile.worker`) copy sources from `Jewel AI/…`.

| Setting | Value |
|---------|-------|
| **Root Directory** | *(leave empty)* — do **not** set to `Jewel AI` |
| API / web config | `railway.toml` → root `Dockerfile` |
| Worker config | `railway.worker.toml` → root `Dockerfile.worker` |

If Root Directory is mistakenly set to `Jewel AI`, either clear it or point the
service config at the nested `Jewel AI/railway.toml` instead. See also
[`docs/DEPLOY_LAYOUT.md`](../DEPLOY_LAYOUT.md).

Catalog / bulk defaults use **Nano Banana Pro Edit** at **1K** resolution for speed. Prefer 4K only when quality requires it (slower and costlier).

After deploying prompt TXT changes, run once:

```bash
cd "Jewel AI/backend"
python -m seeds.migrate_prompt_txt --force
```

Set `SCHEMA_VIA_ALEMBIC=true` in production. The web image runs `alembic upgrade head`
once at container start before uvicorn. With multiple API replicas, prefer a one-shot
migrate job (or single deploy) so concurrent `alembic upgrade` races do not occur.
When Alembic is enabled, the API does **not** run boot-time DDL patches.

## 2. Railway services

Create a project with:

| Service | Dockerfile | Notes |
|---------|------------|--------|
| **web** | root `Dockerfile` | FastAPI + React SPA on `$PORT` |
| **worker** | root `Dockerfile.worker` | Celery worker **with Beat** for stuck/webhook sweeps |
| **PostgreSQL** | Plugin | Auto-injects `DATABASE_URL` — use **one** Postgres only |
| **Redis** | Plugin | Auto-injects `REDIS_URL` (required for auth rate limits in prod) |

**Bulk generation:** keep the **worker** service running. Without Celery workers, the API falls back to in-process threads (`queueMode: inline`) — fine for local/dev, but bulk progress is not durable across API restarts. Studio warns when running inline.

## 3. Environment variables (web + worker)

| Variable | Required | Example |
|----------|----------|---------|
| `NODE_ENV` | yes | `production` |
| `JWT_SECRET` | yes | long random string |
| `FERNET_KEY` | yes | Fernet key |
| `FAL_KEY` | yes | fal.ai API key (generation / paid image calls) |
| `FAL_ADMIN_KEY` | yes* | fal.ai **Admin**-scoped key for header Credits (`GET /account/billing`) |
| `FAL_CREDITS_LOW_THRESHOLD` | no | Low-balance warning threshold (default `5`) |
| `ADMIN_EMAIL` | yes | `admin@jewelai.com` |
| `ADMIN_PASSWORD` | yes | strong (not `changeme`), min 8 chars |
| `DEFAULT_USER_EMAIL` | yes | `studio@jewelai.com` |
| `DEFAULT_USER_PASSWORD` | yes | strong (not `studio123`), min 8 chars |
| `FORCE_SEED_PASSWORDS` | no | `false` — only `true` to reset seed passwords |
| `ALLOW_PROMPT_RESEED` | no | `false` |
| `STORAGE_BACKEND` | yes (prod) | `r2` |
| `R2_*` / Railway `AWS_*` | yes if r2 | bucket credentials |
| `API_PUBLIC_URL` | yes* | public HTTPS URL |
| `FRONTEND_ORIGIN` | yes* | same origin as SPA |
| `SCHEMA_VIA_ALEMBIC` | yes (prod) | `true` |

\*If unset, Railway’s `RAILWAY_PUBLIC_DOMAIN` is applied when placeholders still point at localhost.

\*Without `FAL_ADMIN_KEY`, image generation still works with `FAL_KEY`, but the header shows **Credits: Unavailable** (API-scope keys get 403 on billing). Create an Admin key in the [fal.ai dashboard → Keys](https://fal.ai/dashboard/keys), then add it under Railway → **Jewel-Ai-v3** (and **worker**) → **Variables**.

**Invariant:** web and worker must share the **same** Postgres and Redis.

Worker example:

```
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/1
REDIS_URL=${{Redis.REDIS_URL}}
DATABASE_URL=${{Postgres.DATABASE_URL}}
STORAGE_BACKEND=r2
FAL_KEY=...
FAL_ADMIN_KEY=...
JWT_SECRET=...
FERNET_KEY=...
API_PUBLIC_URL=https://...
NODE_ENV=production
SCHEMA_VIA_ALEMBIC=true
```

## 4. Custom domain

1. Railway → web → **Networking** → **Custom Domain**
2. Add `hj-jewel-ai.data-ikseer.com`
3. DNS CNAME → Railway target

## 5. Local compose (mirrors Railway)

```bash
cd "Jewel AI/deploy/docker"
docker compose up --build
```

- **api**: `alembic upgrade head` then uvicorn; `SCHEMA_VIA_ALEMBIC=true`
- **worker**: Celery worker **with beat** (stuck-job sweep + fal credits refresh)

Docker images install from `backend/requirements.lock.txt` for reproducible deps.
