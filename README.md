# Pyfolio Backend

Backend services for Pyfolio, a long-term portfolio evaluation and planning application. The React frontend lives in a separate repository.

## Architecture and scope

This uv monorepo contains deployable applications under `apps/` and reusable code under `libs/`. `apps/pyfolio-api` provides the REST API; `libs/core` contains shared domain models, validation, persistence, and services. PostgreSQL is the production database. The API and future workers are intended to run as separate containers and share `core` business logic.

The current iteration implements country, currency, security, security quote, and FX rate domain/persistence foundations. HTTP CRUD endpoints are available for countries and securities only. Quote and FX records are managed through shared services for future workers. Currency reference data is intentionally populated by a future dedicated worker; tests create the currency rows they need.

## Requirements and setup

Use Python 3.14 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked --all-packages --all-extras --dev
```

Set `DATABASE_URL` to a PostgreSQL URL, for example:

```text
DATABASE_URL=postgresql+psycopg://pyfolio_app:<password>@localhost:5432/pyfolio
```

The example `postgresql+asyncpg` scheme is also accepted and adapted to the synchronous psycopg driver. SQLite URLs are supported for local tests. Never commit credentials.

Apply migrations from the API package directory:

```bash
cd apps/pyfolio-api
uv run --package pyfolio-api alembic -c alembic.ini upgrade head
uv run --package pyfolio-api uvicorn pyfolio_api.main:app --reload
```

The API listens on `http://127.0.0.1:8000`; interactive OpenAPI docs are at `/docs`. Countries and securities have create, list, retrieve, partial update, and delete endpoints. List endpoints return `items` and `pagination` metadata. They accept `page` (default `1`) and `pageSize` (default `100`, maximum `500`); pagination metadata includes exact filtered item counts and page navigation flags.

## Workspace

```text
apps/pyfolio-api/   FastAPI application, migrations, container image
libs/core/          Shared domain, validation, database models, and services
scripts/            Bootstrap and coverage commands
```

Internal dependencies belong in the consuming member's `[project] dependencies` and `[tool.uv.sources]` with `workspace = true`. Add third-party dependencies through `uv`; keep `uv.lock` committed.

## Development and quality

```bash
uv run --all-packages ruff check .
uv run --all-packages ruff format --check .
uv run --all-packages mypy .
uv run --all-packages pyright
uv run --all-packages pytest
./scripts/run-coverage.sh
```

Tests live beside their package under `tests/`. SQLite is used for fast database/API tests; PostgreSQL-specific concurrency behaviour should be exercised against PostgreSQL when CI infrastructure supports it.

## Docker

Build the API image from the repository root so uv can resolve the workspace:

```bash
docker build --file apps/pyfolio-api/Dockerfile --tag pyfolio-api:latest .
docker run --rm -e DATABASE_URL='postgresql+psycopg://pyfolio_app:password@host.docker.internal:5432/pyfolio' -p 8000:8000 pyfolio-api:latest
```

The image runs as a non-root user. Apply database migrations before starting the API.
