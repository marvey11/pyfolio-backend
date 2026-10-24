# uv Monorepo Template

A small Python monorepo template using [uv](https://docs.astral.sh/uv/), a `src/` layout, Ruff, mypy, pytest, and pre-commit.

## Layout

```text
apps/<application>/       Deployable applications
libs/<library>/            Reusable libraries
```

Each application or library is an independent uv workspace member. The repository root contains shared development dependencies and tool configuration; it is not an importable application package.

## Prerequisites

- Python 3.14 or newer
- uv

Install uv using the [official instructions](https://docs.astral.sh/uv/getting-started/installation/), then create the environment and install all workspace and development dependencies:

```bash
uv sync
```

Commit `uv.lock` whenever dependency metadata changes.

## Add a workspace member

Create a package with uv, then add it to the matching workspace directory:

```bash
uv init --lib --package apps/reporting
uv init --lib --package libs/formatting
```

For an application, place its executable entry point under `src/<package_name>/` and add a console script in its `pyproject.toml` when needed. The root workspace automatically includes directories matching `apps/*` and `libs/*`; run `uv sync` after adding a member.

## Dependencies

Add an external dependency to a specific member with:

```bash
uv add --package runner httpx
```

Add a development-only dependency with `uv add --package runner --dev pytest-mock`. For a dependency used by the whole repository, add it to the root `dev` dependency group:

```bash
uv add --dev coverage
```

For an internal dependency, declare the package name in the consuming member and mark it as a workspace source. For example, `apps/runner/pyproject.toml` contains:

```toml
[project]
dependencies = ["core"]

[tool.uv.sources]
core = { workspace = true }
```

Use the distribution/project name in dependency declarations and the import package name in Python code. uv updates `uv.lock`; do not edit the lockfile manually.

## Commands

Run commands from the repository root. `--all-packages` runs the command in the context of every workspace member.

```bash
# Install or refresh the environment
uv sync --locked --all-packages --all-extras --dev

# Run the sample application
uv run --package runner python -m runner.main

# Run all tests, or one package's tests
uv run --all-packages pytest
uv run pytest libs/core/tests/test_hello.py

# Run all tests, including test coverage
./scripts/run-coverage.sh

# Lint and format
uv run --all-packages ruff check .
uv run --all-packages ruff format --check .
uv run --all-packages ruff format .

# Type-check
uv run --all-packages mypy .
uv run --all-packages pyright
```

To run a command for one member, use `uv run --package <member> <command>`, for example `uv run --package runner pytest`.

## Build the runner image

The runner image uses a multi-stage build and includes the internal `core` dependency. Build it from the repository root so uv can resolve the complete workspace:

```bash
docker build --file apps/runner/Dockerfile --tag uv-runner:latest .
docker run --rm uv-runner:latest
```

## Pre-commit

Install the hooks once, then run them against all files:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
uv run pre-commit run --all-files
```

The pre-commit configuration checks the lockfile, Ruff formatting and linting, TOML/YAML/JSON files, and mypy. The pytest hook runs on pre-push.

Executing `./scripts/bootstrap.sh` will also install the hooks.

## Adding tests

Keep tests in `<member>/tests/`. The root pytest configuration discovers tests below `apps/` and `libs/` and adds each member's `src/` directory to the import path.
