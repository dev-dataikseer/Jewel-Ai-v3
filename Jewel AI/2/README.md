# Jewel AI

Canonical application sources live in **[`Jewel AI/`](./Jewel%20AI/)** (V4).

Railway uses **repo-root** `railway.toml` + `Dockerfile` (Root Directory must stay empty).
See [`Jewel AI/docs/DEPLOY_LAYOUT.md`](./Jewel%20AI/docs/DEPLOY_LAYOUT.md).

```
railway.toml / Dockerfile     ← Railway entrypoints (repo root)
Jewel AI/
  backend/     FastAPI + Celery
  frontend/    React (Vite)
  deploy/      Docker / nginx / env examples
```
