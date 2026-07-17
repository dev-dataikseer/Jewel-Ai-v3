# Jewel AI — Project Structure

Standard monorepo layout for the **Jewel AI** jewelry image studio. Names are chosen so developers and LLM agents can navigate the repository without guessing.

## Repository Layout

The git repository root contains the application folder and a sibling archive:

```text
Jewel AI/                          # Git repository root
├── Jewel AI/                      # ★ Application root (run all commands from here)
│   ├── backend/
│   ├── frontend/
│   ├── data/
│   ├── deploy/
│   ├── docs/
│   ├── scripts/
│   ├── Dockerfile
│   ├── railway.toml
│   ├── RUN.bat
│   └── PROJECT_STRUCTURE.md
└── archive/                       # Retired assets (excluded from the app tree)
```

## Application Layout

```text
Jewel AI/Jewel AI/
├── backend/                 # FastAPI API service (Python)
├── frontend/                # React web application (TypeScript + Vite)
├── data/                    # Non-runtime seed and reference data
├── deploy/                  # Infrastructure, Docker, and deployment configs
├── docs/                    # Product, architecture, and operations documentation
├── scripts/                 # Developer and local environment scripts
├── Dockerfile               # Railway production image (API + built SPA)
├── railway.toml             # Railway API service config
├── railway.worker.toml      # Railway Celery worker config
├── RUN.bat                  # Windows shortcut → scripts/dev-local.bat
├── README.md
└── PROJECT_STRUCTURE.md     # This file
```

## Active Application Code

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI REST API, SQLAlchemy models, prompt pipeline, fal.ai providers, Celery tasks |
| `backend/app/main.py` | API entry point |
| `backend/app/pipeline/` | Prompt composition engine (active) |
| `backend/app/providers/` | AI provider adapters and routing |
| `backend/app/api/routers/` | REST route handlers |
| `backend/seeds/` | Database seeding and one-time prompt template import |
| `backend/tests/` | Pytest test suite |
| `frontend/` | React SPA — Studio, History, Admin, Login |
| `frontend/src/pages/` | Route-level page components |
| `frontend/src/components/` | Reusable UI components |
| `frontend/src/lib/api.ts` | HTTP client for the API |

## Data & Seeds

| Path | Purpose |
| --- | --- |
| `data/seed-prompt-templates/` | Version-controlled `.txt` templates imported once into the database |

Import command:

```bash
cd backend
python -m seeds.migrate_prompt_txt
```

## Deployment

| Path | Purpose |
| --- | --- |
| `deploy/docker/docker-compose.yml` | Local/production multi-service stack (Postgres, Redis, API, worker, web) |
| `deploy/docker/Dockerfile.api` | API + worker base image |
| `deploy/docker/Dockerfile.web` | Nginx frontend image |
| `deploy/docker/Dockerfile.worker` | Celery worker image (Railway) |
| `deploy/nginx/nginx.conf` | Reverse proxy config for the web container |
| `deploy/env/.env.production.example` | Production environment variable template |
| `Dockerfile` | Railway monolith (builds frontend + runs API) |

## Documentation

| Path | Purpose |
| --- | --- |
| `docs/product/` | PRD and end-user web app guide |
| `docs/architecture/` | System design and prompt pipeline |
| `docs/deployment/` | Railway and Docker deployment guides |
| `docs/audits/` | Production readiness and system audit reports |
| `docs/integrations/` | Third-party service notes (e.g. fal.ai) |

## Scripts

| Path | Purpose |
| --- | --- |
| `scripts/dev-local.bat` | Windows one-click local dev (venv, deps, API + Vite) |
| `RUN.bat` | Root-level shortcut for `scripts/dev-local.bat` |

## Archive (Outside Application Tree)

Retired resources live at `../archive/` relative to this folder (git repo root). See `../archive/README.md`.

## Naming Conventions

- **`backend`** / **`frontend`** — standard full-stack monorepo names
- **`deploy/`** — all infrastructure; never mixed with application source
- **`data/`** — static seed files only; runtime uploads live in `backend/uploads/` (gitignored)
- **`archive/`** — anything preserved for history but excluded from builds and imports
- **kebab-case** for directories; **snake_case** for Python modules; **PascalCase** for React components

## Quick Commands

```bash
# Local development (Windows)
RUN.bat

# Backend tests
cd backend && python -m pytest tests/ -q

# Frontend build
cd frontend && npm run build

# Docker Compose (from project root)
docker compose -f deploy/docker/docker-compose.yml up --build
```
