# Jewel AI V3 — Railway deployment

Deploy **Jewel AI V3** to [Railway](https://railway.app) and connect custom domain `hj-jewel-ai.data-ikseer.com`.

## 1. GitHub

Push this repo (`Jewel_V3` folder is the app root). On Railway, set **Root Directory** to `Jewel_V3`.

## 2. Railway services

Create a project with:

| Service | Dockerfile | Notes |
|---------|------------|--------|
| **web** | `Dockerfile` | FastAPI + React SPA on `$PORT` |
| **worker** | `Dockerfile.worker` | Celery image generation |
| **PostgreSQL** | Plugin | Auto-injects `DATABASE_URL` |
| **Redis** | Plugin | Auto-injects `REDIS_URL` |

## 3. Environment variables (web + worker)

| Variable | Required | Example |
|----------|----------|---------|
| `NODE_ENV` | yes | `production` |
| `JWT_SECRET` | yes | long random string |
| `FERNET_KEY` | yes | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `FAL_KEY` | yes | fal.ai API key |
| `ADMIN_EMAIL` | yes | `admin@jewelai.com` |
| `ADMIN_PASSWORD` | yes | strong password |
| `DEFAULT_USER_EMAIL` | yes | `studio@jewelai.com` |
| `DEFAULT_USER_PASSWORD` | yes | strong password |
| `ALLOW_PROMPT_RESEED` | no | `false` |
| `API_PUBLIC_URL` | yes* | `https://hj-jewel-ai.data-ikseer.com` |
| `FRONTEND_ORIGIN` | yes* | `https://hj-jewel-ai.data-ikseer.com` |

\*If unset, Railway’s `RAILWAY_PUBLIC_DOMAIN` is applied automatically when placeholders still point at localhost.

`DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, and `PORT` are set by Railway.

For the worker, set:

```
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/1
REDIS_URL=${{Redis.REDIS_URL}}
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

## 4. Custom domain

1. Railway → web service → **Settings** → **Networking** → **Custom Domain**
2. Add `hj-jewel-ai.data-ikseer.com`
3. Point DNS CNAME to Railway’s target
4. Set `API_PUBLIC_URL` and `FRONTEND_ORIGIN` to `https://hj-jewel-ai.data-ikseer.com`

## 5. Verify

- `GET https://hj-jewel-ai.data-ikseer.com/health` → `database: true`, `redis: true`
- Login as admin → **Admin → Users** loads (no “Try again”)
- Studio generate completes (worker service running)

## Local Docker (optional)

```bash
cd Jewel_V3/config
docker compose up -d --build
```
