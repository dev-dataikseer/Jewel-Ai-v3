# Jewel AI V3 — Railway deployment

Deploy **Jewel AI V3** to [Railway](https://railway.app) and connect custom domain `hj-jewel-ai.data-ikseer.com`.

Repo: https://github.com/dev-dataikseer/Jewel-Ai-v3

Clone this repository — set Railway **Root Directory** to `Jewel AI` (the application lives in that subfolder; `archive/` stays at repo root).

Catalog / bulk defaults use **Nano Banana Pro Edit** at **1K** resolution for speed. Prefer 4K only when quality requires it (slower and costlier).

After deploying prompt TXT changes, run once:

```bash
cd backend
python -m seeds.migrate_prompt_txt --force
```

Set `SCHEMA_VIA_ALEMBIC=true` in production and run `alembic upgrade head` before starting the API.

## 2. Railway services

Create a project with:

| Service | Dockerfile | Notes |
|---------|------------|--------|
| **web** | `Dockerfile` | FastAPI + React SPA on `$PORT` |
| **worker** | `deploy/docker/Dockerfile.worker` | Celery worker **with Beat** for stuck/webhook sweeps |
| **PostgreSQL** | Plugin | Auto-injects `DATABASE_URL` — use **one** Postgres only |
| **Redis** | Plugin | Auto-injects `REDIS_URL` |

## 3. Environment variables (web + worker)

| Variable | Required | Example |
|----------|----------|---------|
| `NODE_ENV` | yes | `production` |
| `JWT_SECRET` | yes | long random string |
| `FERNET_KEY` | yes | Fernet key |
| `FAL_KEY` | yes | fal.ai API key |
| `ADMIN_EMAIL` | yes | `admin@jewelai.com` |
| `ADMIN_PASSWORD` | yes | strong (not `changeme`) |
| `DEFAULT_USER_EMAIL` | yes | `studio@jewelai.com` |
| `DEFAULT_USER_PASSWORD` | yes | strong (not `studio123`) |
| `FORCE_SEED_PASSWORDS` | no | `false` — only `true` to reset seed passwords |
| `ALLOW_PROMPT_RESEED` | no | `false` |
| `STORAGE_BACKEND` | yes (prod) | `r2` |
| `R2_*` / Railway `AWS_*` | yes if r2 | bucket credentials |
| `API_PUBLIC_URL` | yes* | public HTTPS URL |
| `FRONTEND_ORIGIN` | yes* | same origin as SPA |

\*If unset, Railway’s `RAILWAY_PUBLIC_DOMAIN` is applied when placeholders still point at localhost.

**Invariant:** web and worker must share the **same** Postgres and Redis.

Worker example:

```
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/1
REDIS_URL=${{Redis.REDIS_URL}}
DATABASE_URL=${{Postgres.DATABASE_URL}}
STORAGE_BACKEND=r2
FAL_KEY=...
JWT_SECRET=...
FERNET_KEY=...
API_PUBLIC_URL=https://...
NODE_ENV=production
```

## 4. Custom domain

1. Railway → web → **Networking** → **Custom Domain**
2. Add `hj-jewel-ai.data-ikseer.com`
3. DNS CNAME → Railway target
4. Set `API_PUBLIC_URL` / `FRONTEND_ORIGIN` to that HTTPS URL

## 5. Verify

- `GET /health` → `database: true` (HTTP 503 if DB down)
- Admin → **Monitoring** loads
- Studio generate completes (worker + Beat)
- Unsigned `/uploads/...` → 401

## Local Docker (optional)

```bash
cd config
docker compose up -d --build
```
