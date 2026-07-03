# Security Policy

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security reports.

Email the maintainer directly with a description of the issue and steps to
reproduce. You should receive an acknowledgment within 72 hours.

## Supported versions

Only the latest `main` branch is supported.

## Handling of secrets

- All secrets are loaded from environment variables via `.env` files that are
  git-ignored. See `.env.example` for the full list of required variables.
- The Docker image runs as a non-root `trade` user.
- CI runs `pip-audit` and `trivy fs` on every push.
- `gitleaks` runs in `pre-commit` to catch secrets before they land in a commit.

## Production credentials

- Always start on **testnet / paper** (`TRADE_ENV=staging`). The default in
  `.env.example` sets `BINANCE_TESTNET=true`.
- Store production credentials in a secrets manager (Vault, AWS Secrets Manager,
  1Password Connect, etc.), not in the shell history.
- Rotate credentials on any suspected exposure or after an operator leaves.
- Never commit an `.env` file. `pre-commit` will block it.
