"""Strategy / venue YAML config loader.

Runtime configs live in `configs/strategies/*.yaml` and `configs/venues/*.yaml`.
Kept separate from typed pydantic Settings (which handle env/secrets) so that
strategy parameters can be version-controlled, diffed, and promoted independently.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_ROOT = Path(__file__).resolve().parent.parent.parent / "configs"


def load_strategy_config(name: str, explicit_path: Path | None = None) -> dict[str, Any]:
    """Load a strategy config by name (e.g. `ema_cross`) or explicit path."""
    if explicit_path is not None:
        path = explicit_path
    else:
        path = CONFIG_ROOT / "strategies" / f"{name}.yaml"

    if not path.exists():
        raise FileNotFoundError(
            f"Strategy config not found: {path}. "
            f"Available: {list((CONFIG_ROOT / 'strategies').glob('*.yaml'))}"
        )
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Strategy config {path} did not parse as a mapping")
    return data


def load_venue_config(name: str) -> dict[str, Any]:
    """Load a venue config by name (e.g. `binance`)."""
    path = CONFIG_ROOT / "venues" / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Venue config not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Venue config {path} did not parse as a mapping")
    return data
