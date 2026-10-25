# AGENTS.md

## Repository scope

This is the Pyfolio backend uv monorepo. Deployable applications live in `apps/`; reusable domain and service code lives in `libs/`. Each workspace member is an independent Python package with a `src/` layout. The root project is tooling-only and must not become an application package.

`apps/pyfolio-api` owns HTTP routes, Pydantic API schemas, database migrations, and its container image. `libs/core` owns shared domain entities, validation, persistence models, and application services used by the API and future workers.

## Development workflow

* Use Python 3.14 or newer.
* After project metadata or lockfile changes, run `uv sync --locked --all-packages --all-extras --dev`.
* Keep `uv.lock` committed and current. Add dependencies with uv, not by hand-editing the lockfile.
* Run Ruff lint and format checks, mypy, pyright, pytest, and coverage before submitting changes; report checks that could not run and measured coverage.
* Prefer `uv run --package <member> ...` for checks scoped to one workspace member.
* Format with Ruff and use absolute imports.

## Workspace dependencies

Declare internal dependencies in the consuming member's `[project] dependencies` and add a matching `[tool.uv.sources]` entry with `workspace = true`. Keep reusable business rules in `core`; add a new package only when the repository design warrants it.

## Architecture and data integrity

* Keep HTTP concerns in `pyfolio-api`; do not expose ORM entities as API responses.
* Use Pydantic for request/response validation and SQLAlchemy for persistence.
* Keep database constraints for uniqueness, foreign keys, and required values. Read credentials only from environment configuration and never log connection strings or secrets.
* `Currency` is a dedicated entity. Production currency reference data is maintained by a future worker; tests may create the rows they require.
* Quotes and FX rates are worker/service data, not REST resources. Quote exchange canonicalisation is trim plus uppercase. FX rates use foreign currency units per EUR 1.00, with EUR implicit.
* Use Alembic for database schema changes.

## Testing

Tests live in each member's `tests/` directory. The root pytest configuration discovers tests beneath `apps/` and `libs/`. SQLite is suitable for ordinary unit and API integration tests but does not model PostgreSQL concurrency semantics; use PostgreSQL-backed integration tests where those behaviours matter.
