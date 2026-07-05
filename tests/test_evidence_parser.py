"""Evidence parser tests."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from evidence_parser import parse_evidence

FIXTURES = Path(__file__).parent / "fixtures" / "evidence"


class TestEvidenceParser:
    def test_parse_pass_evidence(self) -> None:
        report = parse_evidence(FIXTURES / "evidence_PASS.md")
        assert report.status == "PASS"
        assert report.run_id == "smoke01"
        assert report.reconciliation_ok is True
