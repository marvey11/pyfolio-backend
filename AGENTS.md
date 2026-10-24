# AGENTS.md

## Repository scope

This repository is a Python monorepo managed by uv. Applications live under `apps/`, reusable libraries live under `libs/`, and each workspace member is an independent Python package with a `src/` layout.

The root project is tooling-only. Do not add application code or make the root package installable unless the repository design changes intentionally.

## Development workflow

* Use Python 3.14 or newer, as specified by `.python*version` and the project metadata.
* Run `uv sync --locked --all-packages --all-extras --dev` after changing project metadata or the lockfile.
* Keep `uv.lock` committed and up to date.
* Run `uv run --all-packages ruff check .`, `uv run --all-packages ruff format --check .`, `uv run --all-packages mypy .`, `uv run --all-packages pyright`, and `uv run --all-packages pytest` before submitting changes.
* Prefer `uv run --package <member> ...` when checking one workspace member.
* Format with Ruff and keep imports absolute.

## Workspace dependencies

* Add internal dependencies to the consuming member's `[project] dependencies`.
* Add the matching `[tool.uv.sources]` entry with `workspace = true`.
* Add third-party dependencies with uv rather than editing `uv.lock` by hand.

## Testing

Tests are discovered from `apps/` and `libs/`. The root pytest configuration adds each member's `src/` directory to the test import path, so tests can import installed package names while running from the repository root.

Keep tests close to the package they cover, in that package's `tests/` directory.
