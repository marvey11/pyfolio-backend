FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY apps/pyfolio-api/pyproject.toml apps/pyfolio-api/README.md apps/pyfolio-api/
COPY libs/core/pyproject.toml libs/core/README.md libs/core/
RUN uv sync --frozen --no-dev --no-install-workspace --package pyfolio-api
COPY apps/pyfolio-api/src apps/pyfolio-api/src
COPY libs/core/src libs/core/src
RUN uv sync --frozen --no-dev --no-editable --package pyfolio-api

FROM python:3.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN groupadd -g 999 appuser && useradd -r -u 999 -g appuser appuser
COPY --from=builder /app/.venv /app/.venv
COPY apps/pyfolio-api/alembic.ini /app/alembic.ini
COPY apps/pyfolio-api/migrations /app/migrations
USER appuser
EXPOSE 8000
CMD ["uvicorn", "pyfolio_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
