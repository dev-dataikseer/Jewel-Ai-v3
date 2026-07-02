# Jewel AI V3

Premium AI jewelry studio — FastAPI + React + fal.ai.

**GitHub:** https://github.com/dev-dataikseer/Jewel-Ai-v3  
**Production:** https://jewel-ai.up.railway.app

## Quick Start

Double-click `RUN.bat` for local Windows development.

- API: http://localhost:8000
- App: http://localhost:5173

## Default Accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@jewelai.com | changeme |
| User | studio@jewelai.com | studio123 |

## Folder Structure

```text
Jewel_V3/
├── backend/          FastAPI API, SQLAlchemy models, prompt engine, providers, Celery tasks
├── frontend/         React/Vite luxury Studio, History, and Admin UI
├── prompts/          TXT prompt library for seeded workflow templates
├── docs/             PRD, prompt pipeline docs, and v3 architecture blueprint
├── config/           Docker Compose, Dockerfiles, Nginx, production env example
└── RUN.bat           Windows local launcher
```

## Manual Run

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set PYTHONPATH=.
set DATABASE_URL=sqlite:///./jewel.db
uvicorn app.main:app --reload --port 8000

# Frontend, in a separate terminal
cd frontend
npm install
npm run dev
```

On Windows, if `python` is not on PATH but the Python launcher exists, use `py -3` in place of `python`.

## Tests

```bash
cd backend
python -m pytest tests/ -q

cd frontend
npm run build
```

## Configuration

Copy `backend/.env.local.example` to `backend/.env` and set `FAL_KEY` for fal.ai image generation.

## Production Compose

```bash
cd config
docker compose up --build
```

Review `config/.env.production.example` before deploying.

## Architecture

Read `docs/ARCHITECTURE_BLUEPRINT.md` for the codebase analysis, v3 consolidation decisions, backend layer map, prompt-engine matrix, and deployment notes.
