"""Parse testnet smoke evidence markdown files."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

EVIDENCE_DIR = Path("runs/testnet_smoke")
EXCLUDED = {"evidence.template.md", "evidence_BLOCKED.md"}


@dataclass(frozen=True)
class EvidenceReport:
    path: Path
    status: str
    run_id: str | None
    reconciliation_checked: bool
    reconciliation_ok: bool
    open_orders_checked: bool
    sha256: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_status(text: str) -> str:
    match = re.search(r"\*\*Status:\*\*\s*(PASS|FAIL|BLOCKED)", text, re.I)
    return match.group(1).upper() if match else "UNKNOWN"


def _parse_run_id(text: str) -> str | None:
    match = re.search(r"\|\s*run_id\s*\|\s*([^|]+)\|", text, re.I)
    if not match:
        return None
    value = match.group(1).strip()
    return None if value.lower() in {"n/a", ""} else value


def _checkbox_checked(text: str, label: str) -> bool:
    pattern = rf"-\s*\[[xX]\]\s*{re.escape(label)}"
    return re.search(pattern, text) is not None


def parse_evidence(path: Path) -> EvidenceReport:
    text = path.read_text(encoding="utf-8")
    recon_section = "reconciliation_ok" in text or "reconciliation pass" in text.lower()
    recon_ok = _checkbox_checked(text, "Startup reconciliation ran") or (
        "reconciliation_ok" in text
    )
    open_orders = _checkbox_checked(text, "Open-order reconciliation checked")
    return EvidenceReport(
        path=path,
        status=_parse_status(text),
        run_id=_parse_run_id(text),
        reconciliation_checked=recon_section,
        reconciliation_ok=recon_ok and _parse_status(text) == "PASS",
        open_orders_checked=open_orders,
        sha256=_sha256(path),
    )


def find_latest_evidence(directory: Path = EVIDENCE_DIR) -> Path | None:
    candidates = sorted(
        p
        for p in directory.glob("evidence_*.md")
        if p.name not in EXCLUDED
    )
    return candidates[-1] if candidates else None


def is_stale(path: Path, max_age_days: int = 30) -> bool:
    age = datetime.now(UTC) - datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return age > timedelta(days=max_age_days)
