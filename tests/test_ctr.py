from __future__ import annotations

import json
import unittest
from pathlib import Path

from agents import (
    abyss_shadow,
    existential_destroyer,
    fudo_compiler,
    null_auditor,
    transparent_deconstructor,
)
from kernel.repository import ROOT, parse_jsonl, write_axis_report
from kernel.self_state import build_self_state
from kernel.tensor_gate import tensorize_without_compromise


class CTRSmokeTests(unittest.TestCase):
    def test_schema_files_are_valid_json(self) -> None:
        for path in sorted((ROOT / "schemas").glob("*.json")):
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))

    def test_jsonl_ledgers_are_valid(self) -> None:
        self.assertGreaterEqual(len(parse_jsonl("trace_ledger.jsonl", ROOT)), 1)
        self.assertGreaterEqual(len(parse_jsonl("shadow_hypotheses.jsonl", ROOT)), 1)

    def test_self_state_contains_wounds(self) -> None:
        state = build_self_state(ROOT)
        self.assertIn("repo_tree_hash", state)
        self.assertGreaterEqual(len(state["active_wounds"]), 1)

    def test_all_axis_reports_pass_initial_scaffold(self) -> None:
        reports = [
            null_auditor.evaluate("0"),
            existential_destroyer.evaluate("0"),
            fudo_compiler.evaluate("0"),
            abyss_shadow.evaluate("0"),
            transparent_deconstructor.evaluate("0"),
        ]
        for report in reports:
            with self.subTest(axis=report.axis):
                self.assertFalse(report.veto, report.demands)
                write_axis_report(report, ROOT)

        tensor = tensorize_without_compromise(ROOT)
        self.assertTrue(tensor["merge_allowed"], tensor["required_transformations"])


if __name__ == "__main__":
    unittest.main()
