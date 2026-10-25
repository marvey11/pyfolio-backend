# pyfolio-api

FastAPI application exposing CRUD endpoints for countries and securities. Request and response payloads use Pydantic schemas; shared rules and database models come from `core`. Lists use offset pagination (`offset=0`, `limit=100`, maximum `500`). Unique or referential integrity conflicts return HTTP 409; missing resources return 404 and invalid requests use FastAPI's 422 response.

WKN values use six uppercase letters or digits. Exchange identifiers for stored quotes are trimmed and uppercased.

Set `DATABASE_URL` before starting the application. PostgreSQL is the production database; SQLite is supported for tests. The API accepts `postgresql+psycopg`, `postgresql+asyncpg` (adapted to psycopg), `postgresql`, and SQLite URLs. Run migrations before starting:

```bash
uv run --package pyfolio-api alembic -c alembic.ini upgrade head
uv run --package pyfolio-api uvicorn pyfolio_api.main:app --reload
```

Run package tests with `uv run --package pyfolio-api pytest apps/pyfolio-api/tests`. Build its production container from the repository root with `docker build -f apps/pyfolio-api/Dockerfile .`.
