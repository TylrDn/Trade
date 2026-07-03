# ADR 0001 — Adopt `src/` package layout

- Status: Accepted
- Date: 2026-07-03

## Context

The initial repo placed the `nautilus_trade` package at the repository root.
That makes it importable directly from a checkout without installing it, which
is convenient but hides packaging bugs: relative imports, missing files in the
wheel, and namespace collisions with `tests/` or `scripts/` all go undetected
until distribution time.

Additionally, we want to publish a wheel (`nautilus-trade-0.2.0-py3-none-any.whl`)
that installs cleanly into a fresh venv, with `py.typed` shipped alongside.

## Decision

Move the package into `src/nautilus_trade/`. Consumers now install with
`pip install -e .` and the wheel build is validated on every CI run.

## Consequences

- `import nautilus_trade` requires an install (`pip install -e .`), which
  matches how real users will consume the package.
- CI catches packaging regressions immediately.
- Editors and mypy discover the package from the installed distribution, not
  the source root, which prevents accidental picks of a stale copy on `sys.path`.
- Tests must not `sys.path.insert(0, "src")` — they rely on the installed dist.

## Alternatives considered

- **Flat layout at repo root.** Rejected: hides packaging issues.
- **Namespace package (`nautilus_trade.<sub>`) split across repos.** Rejected:
  the system is a single deployable unit; namespace fragmentation costs more
  than it buys.
