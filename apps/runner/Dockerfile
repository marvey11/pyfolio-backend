# ==========================================
# Stage 1: Build & Dependency Resolution
# ==========================================
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy workspace metadata files to cache dependency installation
COPY pyproject.toml uv.lock ./
COPY apps/runner/pyproject.toml apps/runner/README.md ./apps/runner/
COPY libs/core/pyproject.toml libs/core/README.md ./libs/core/

# Sync dependencies without non-required packages or editable installs first
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package runner

# Copy full source code for workspace packages
COPY apps/runner/src ./apps/runner/src
COPY libs/core/src ./libs/core/src

# Perform final sync to install workspace packages into environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package runner

# ==========================================
# Stage 2: Minimal Production Runtime
# ==========================================
FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Create a non-root user for runtime security
RUN groupadd -g 999 appuser && \
    useradd -r -u 999 -g appuser appuser

# Copy installed virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

USER appuser

ENTRYPOINT ["python", "-m", "runner.main"]
