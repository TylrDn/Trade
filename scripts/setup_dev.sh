#!/usr/bin/env bash
# Bootstrap a local dev environment for Phase 11 staging smoke.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pick_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    echo "$PYTHON"
    return
  fi
  for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$(command -v "$candidate")"
      return
    fi
  done
  echo "python3 not found" >&2
  exit 1
}

PY="$(pick_python)"

if "$PY" -c 'import sys; raise SystemExit(1 if "Cursor" in sys.executable or "AppImage" in sys.executable else 0)'; then
  echo "ERROR: $PY resolves to an IDE shim: $("$PY" -c 'import sys; print(sys.executable)')" >&2
  echo "Run from a normal terminal, or set PYTHON explicitly, e.g.:" >&2
  echo "  PYTHON=/usr/bin/python3.12 $0" >&2
  exit 1
fi

echo "Using Python: $PY ($("$PY" --version))"

if [[ -d .venv ]]; then
  if readlink .venv/bin/python 2>/dev/null | grep -qE 'Cursor|AppImage'; then
    echo "Removing broken .venv (IDE python shim detected)"
    rm -rf .venv
  fi
fi

if [[ ! -d .venv ]]; then
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev,kraken]"

if [[ ! -f .env ]]; then
  cp .env.example .env
  sed -i 's/^TRADE_ENV=research/TRADE_ENV=staging/' .env
  echo "Created .env (TRADE_ENV=staging, TRADE_VENUE=kraken). Add KRAKEN_FUTURES_DEMO_* keys."
else
  echo ".env already exists — not overwriting."
fi

mkdir -p logs/events runs/testnet_smoke

echo ""
echo "=== Verification ==="
python scripts/smoke_testnet.py --dry-run
python -m pytest tests/test_smoke_testnet.py tests/test_soak_status.py tests/test_evidence_parser.py \
  tests/test_kraken_auth.py tests/test_kraken_instruments.py tests/test_kraken_snapshot.py \
  tests/test_venue_registry.py -v

echo ""
echo "=== Ready for Phase 11a (Kraken demo) ==="
echo "1. Sign up at https://demo-futures.kraken.com and create Full access API keys"
echo "2. Edit .env: KRAKEN_FUTURES_DEMO_API_KEY, KRAKEN_FUTURES_DEMO_API_SECRET"
echo "3. source .venv/bin/activate"
echo "4. TRADE_ENV=staging python scripts/run_live.py"
echo "5. python scripts/smoke_testnet.py --events ./logs/events/events_<run_id>.jsonl"
echo "See runs/testnet_smoke/MANUAL_OPS.md and docs/testnet_smoke.md"
