# Jewel AI V4 — production image (API + built React SPA)
# Build context: git repository root (Railway Root Directory empty).
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY ["Jewel AI/frontend/package.json", "Jewel AI/frontend/package-lock.json", "./"]
RUN npm ci
COPY ["Jewel AI/frontend", "./"]
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV NODE_ENV=production
ENV SCHEMA_VIA_ALEMBIC=true

COPY ["Jewel AI/backend/requirements.lock.txt", "/app/requirements.txt"]
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ["Jewel AI/backend", "/app"]
COPY ["Jewel AI/data/seed-prompt-templates", "/app/data/seed-prompt-templates"]
COPY --from=frontend-build /app/frontend/dist /app/static

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
