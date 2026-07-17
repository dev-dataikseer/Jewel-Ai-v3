# Jewel AI V4 — production image (API + built React SPA)
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV NODE_ENV=production
ENV SCHEMA_VIA_ALEMBIC=true

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app
COPY data/seed-prompt-templates /app/data/seed-prompt-templates
COPY --from=frontend-build /app/frontend/dist /app/static

EXPOSE 8000
# Migrate schema before serving (SCHEMA_VIA_ALEMBIC skips create_all on boot).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
