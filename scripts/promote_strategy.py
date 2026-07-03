"""Strategy promotion script.

Runs pre-promotion checklist and records the promotion manifest.
Do not promote a strategy to a higher environment without passing all gates.

Usage:
    python scripts/promote_strategy.py --strategy ema_cross --from research --to staging
    python scripts/promote_strategy.py --strategy ema_cross --from staging --to production
"""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

PROMOTION_DIR = Path("./runs/promotions")

# Checklist gates per promotion path
GATES: dict[str, list[str]] = {
    "research->staging": [
        "Backtest manifest exists with reproducible output",
        "Parameter sensitivity analysis completed",
        "Strategy-local risk limits verified in backtest",
        "No open TODO/FIXME in strategy module",
    ],
    "staging->production": [
        "Paper node ran for >= 7 days with no reconciliation failures",
        "Emergency flatten tested in staging",
        "All circuit breakers verified tripping correctly",
        "Feed-failure recovery test passed",
        "Ops alerts verified firing correctly",
        "Position sizing reviewed at target capital level",
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote strategy to next environment")
    parser.add_argument("--strategy", required=True, help="Strategy name")
    parser.add_argument("--from", dest="from_env", required=True)
    parser.add_argument("--to", dest="to_env", required=True)
    parser.add_argument("--operator", default="", help="Operator ID or name")
    args = parser.parse_args()

    path_key = f"{args.from_env}->{args.to_env}"
    gates = GATES.get(path_key, [])

    print(f"\nPromotion checklist: {args.strategy} ({path_key})\n")
    passed = []
    for gate in gates:
        resp = input(f"  [ ] {gate} — passed? (y/n): ").strip().lower()
        passed.append({"gate": gate, "passed": resp == "y"})

    failed = [g for g in passed if not g["passed"]]
    if failed:
        log.error("Promotion BLOCKED — %d gate(s) not passed:", len(failed))
        for f in failed:
            log.error("  FAIL: %s", f["gate"])
        return

    promo_id = str(uuid.uuid4())[:8]
    manifest = {
        "promo_id": promo_id,
        "strategy": args.strategy,
        "from_env": args.from_env,
        "to_env": args.to_env,
        "operator": args.operator,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gates": passed,
    }

    PROMOTION_DIR.mkdir(parents=True, exist_ok=True)
    out = PROMOTION_DIR / f"promo_{promo_id}.json"
    out.write_text(json.dumps(manifest, indent=2))
    log.info("✅ Promotion APPROVED: %s → %s (manifest: %s)", args.from_env, args.to_env, out)


if __name__ == "__main__":
    main()
