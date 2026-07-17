# Jewel AI

Premium AI jewelry studio — FastAPI backend + React frontend + fal.ai image generation.

**GitHub:** https://github.com/dev-dataikseer/Jewel-Ai-v3  
**Production:** https://jewel-ai.up.railway.app

## Quick Start

Double-click `RUN.bat` (or run `scripts/dev-local.bat`) for local Windows development.

- API: http://localhost:8000
- App: http://localhost:5173

## Default Accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@jewelai.com | changeme |
| User | studio@jewelai.com | studio123 |

## Project Structure

See **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** for the full directory map.

```text
Jewel AI/                  # Git repo root
├── Jewel AI/              # ★ Application root — open and run from here
│   ├── backend/
│   ├── frontend/
│   ├── data/
│   ├── deploy/
│   ├── docs/
│   └── scripts/
└── archive/               # Retired code and media (sibling, not in app tree)
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
docker compose -f deploy/docker/docker-compose.yml up --build
```

Review `deploy/env/.env.production.example` before deploying.

## Architecture

Read `docs/architecture/ARCHITECTURE_BLUEPRINT.md` for the codebase analysis, consolidation decisions, backend layer map, prompt-engine matrix, and deployment notes.
