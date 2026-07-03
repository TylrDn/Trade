# Contributing

Thanks for helping improve `nautilus-trade`. Trading systems are unforgiving,
so the bar for changes to risk, execution, and live paths is intentionally high.

## Local setup

```bash
git clone https://github.com/TylrDn/Trade.git
cd Trade
python -m venv .venv && source .venv/bin/activate
make install-dev
make pre-commit-install
```

## Workflow

1. Create a branch off `main`: `git checkout -b feat/short-name`.
2. Keep commits small and focused. Reference an issue when applicable.
3. Run `make lint typecheck test` locally before pushing.
4. Open a PR against `main` using the template. Fill every checklist item.

## Coding standards

- Python 3.11+, fully type-annotated.
- `ruff` for lint + format, `mypy --strict` for typing.
- No `# type: ignore` without a comment explaining the case.
- No blocking network calls on hot paths (order submission, on_bar, on_quote).
- Every alert / halt call must be idempotent.

## Testing

- Unit tests: fast, no network, no filesystem beyond `tmp_path`.
- Integration tests: marked with `@pytest.mark.integration`.
- Long-running / market data tests: marked `@pytest.mark.slow`.
- New strategy logic must include tests exercising the entry, exit, and
  strategy-local risk gate.

## Risk-critical changes

Changes under `src/nautilus_trade/risk/`, `src/nautilus_trade/execution/`, or
`src/nautilus_trade/live/` require:

- A dedicated test proving the new behavior.
- A note in the PR describing the failure modes considered.
- Review from a listed owner in `.github/CODEOWNERS`.

## Promoting strategies

Never promote a strategy to a higher environment without running
`trade promote --strategy X --from Y --to Z` and passing every gate.
See [docs/PROMOTION.md](docs/PROMOTION.md) for the full checklist.
