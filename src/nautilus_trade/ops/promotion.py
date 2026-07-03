"""Strategy promotion runner.

Extracted from scripts/promote_strategy.py so the logic is unit-testable
and the CLI subcommand can delegate to a single source of truth.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

PROMOTION_DIR = Path("./runs/promotions")

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


def run_promotion(
    strategy: str,
    from_env: str,
    to_env: str,
    operator: str = "",
    responses: list[bool] | None = None,
) -> tuple[bool, Path | None]:
    """Run promotion gates.

    Args:
        responses: If provided, use these (True/False per gate) instead of
            prompting interactively. Enables unit-testable promotion runs.

    Returns:
        (ok, manifest_path). manifest_path is None when blocked.
    """
    path_key = f"{from_env}->{to_env}"
    gates = GATES.get(path_key)
    if gates is None:
        log.error("No promotion path defined: %s", path_key)
        return False, None

    print(f"\nPromotion checklist: {strategy} ({path_key})\n")
    passed: list[dict[str, bool | str]] = []
    for i, gate in enumerate(gates):
        if responses is not None:
            ok = responses[i]
        else:
            resp = input(f"  [ ] {gate} — passed? (y/n): ").strip().lower()
            ok = resp == "y"
        passed.append({"gate": gate, "passed": ok})

    failed = [g for g in passed if not g["passed"]]
    if failed:
        log.error("Promotion BLOCKED — %d gate(s) not passed:", len(failed))
        for f in failed:
            log.error("  FAIL: %s", f["gate"])
        return False, None

    promo_id = str(uuid.uuid4())[:8]
    manifest = {
        "promo_id": promo_id,
        "strategy": strategy,
        "from_env": from_env,
        "to_env": to_env,
        "operator": operator,
        "timestamp": datetime.now(UTC).isoformat(),
        "gates": passed,
    }
    PROMOTION_DIR.mkdir(parents=True, exist_ok=True)
    out = PROMOTION_DIR / f"promo_{promo_id}.json"
    out.write_text(json.dumps(manifest, indent=2))
    log.info("Promotion APPROVED: %s -> %s (manifest: %s)", from_env, to_env, out)
    return True, out
