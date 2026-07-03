"""Promotion runner tests (non-interactive)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nautilus_trade.ops import promotion as promo


@pytest.fixture(autouse=True)
def _redirect_promo_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(promo, "PROMOTION_DIR", tmp_path / "promotions")


class TestRunPromotion:
    def test_all_gates_pass_writes_manifest(self, tmp_path: Path) -> None:
        gates = promo.GATES["research->staging"]
        ok, out = promo.run_promotion(
            strategy="ema_cross",
            from_env="research",
            to_env="staging",
            operator="tdean",
            responses=[True] * len(gates),
        )
        assert ok is True
        assert out is not None
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["strategy"] == "ema_cross"
        assert data["operator"] == "tdean"
        assert all(g["passed"] for g in data["gates"])

    def test_any_failed_gate_blocks(self) -> None:
        gates = promo.GATES["staging->production"]
        responses = [True] * len(gates)
        responses[2] = False
        ok, out = promo.run_promotion(
            strategy="ema_cross",
            from_env="staging",
            to_env="production",
            responses=responses,
        )
        assert ok is False
        assert out is None

    def test_unknown_path_rejected(self) -> None:
        ok, out = promo.run_promotion(
            strategy="ema_cross",
            from_env="production",
            to_env="research",
            responses=[],
        )
        assert ok is False
        assert out is None
