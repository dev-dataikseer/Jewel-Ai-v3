"""Schema ownership note.

Production should set SCHEMA_VIA_ALEMBIC=true and run:

    cd backend
    alembic upgrade head

When SCHEMA_VIA_ALEMBIC is false (default for local SQLite), the API still uses
SQLAlchemy create_all + additive db_migrate helpers for convenience.

Alembic revisions 001–003 exist under alembic/versions/. Prefer expanding Alembic
for all future schema changes and retiring create_all in production.
"""
