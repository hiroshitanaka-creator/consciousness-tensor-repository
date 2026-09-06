from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernel.experience_event import build_experience_event, ingest
from kernel.ledger import sha256_text
from kernel.repository import ROOT, parse_jsonl


def issue_payload() -> dict:
    return {
        "action": "opened",
        "repository": {"full_name": "example/ctr"},
        "issue": {
            "number": 52,
            "title": "Add conversational memory",
            "body": "Preserve history and audit every automatic decision.",
            "state": "open",
            "created_at": "2026-07-01T12:00:00Z",
            "updated_at": "2026-07-01T12:00:00Z",
        },
    }


class ExperienceEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "contradiction_matrix.json").write_bytes((ROOT / "contradiction_matrix.json").read_bytes())

    def read_event(self, result: dict) -> dict:
        return json.loads((self.root / result["path"]).read_text(encoding="utf-8"))

    def test_issue_becomes_attributable_unassimilated_observation(self) -> None:
        result = ingest(issue_payload(), self.root)
        event = self.read_event(result)
        self.assertEqual(event["event_id"], "event:example/ctr:issue-52")
        self.assertEqual(event["initial_status"], "unassimilated")
        self.assertEqual(event["source"]["body"], issue_payload()["issue"]["body"])
        self.assertEqual(set(event["possible_wounds"]), {
            "observation-vs-task", "minimality-vs-ecology", "transparency-vs-shadow", "comfort-vs-decision",
        })
        trace, = parse_jsonl("trace_ledger.jsonl", self.root)
        self.assertEqual(trace["model"], "none")
        self.assertEqual(trace["output_hash"], sha256_text((self.root / result["path"]).read_text(encoding="utf-8")))
        self.assertIn(event["source"]["url"] + "@" + event["revision_id"], trace["input_sources"])
        self.assertEqual(event["decay"]["review_after"], "2026-09-29T12:00:00+00:00")

    def test_replay_leaves_files_and_trace_byte_identical(self) -> None:
        result = ingest(issue_payload(), self.root)
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        replay = ingest(issue_payload(), self.root)
        self.assertFalse(replay["created"])
        self.assertFalse(replay["trace_appended"])
        self.assertEqual(result["path"], replay["path"])
        self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})

    def test_edited_reopened_and_out_of_order_deliveries_preserve_revisions(self) -> None:
        original = issue_payload()
        edited = copy.deepcopy(original)
        edited["action"] = "edited"
        edited["issue"].update(body="Remove memory", updated_at="2026-07-02T12:00:00Z")
        reopened = copy.deepcopy(edited)
        reopened["action"] = "reopened"
        reopened["issue"]["updated_at"] = "2026-07-03T12:00:00Z"
        results = [ingest(payload, self.root) for payload in (reopened, edited, original)]
        self.assertEqual(len({result["path"] for result in results}), 3)
        self.assertEqual(len({self.read_event(result)["event_id"] for result in results}), 1)
        self.assertEqual(len(parse_jsonl("trace_ledger.jsonl", self.root)), 3)

    def test_null_body_and_unknown_request_stay_unassimilated(self) -> None:
        payload = issue_payload()
        payload["issue"].update(title="Change heading", body=None)
        event = build_experience_event(payload, self.root)
        self.assertEqual(event["source"]["body"], "")
        self.assertEqual(event["possible_wounds"], ["observation-vs-task"])

    def test_japanese_matching_is_explicit_and_provisional(self) -> None:
        payload = issue_payload()
        payload["issue"].update(title="\u8a18\u61b6\u306e\u524a\u9664", body="\u76e3\u67fb\u3068\u6c7a\u65ad")
        event = build_experience_event(payload, self.root)
        self.assertEqual(len(event["possible_wounds"]), 4)
        self.assertTrue(event["classification"]["requires_review"])
        self.assertIn("\u8a18\u61b6", event["classification"]["matched_terms"]["minimality-vs-ecology"])

    def test_invalid_external_inputs_write_nothing(self) -> None:
        bad_values = [
            ("number", "../../escape"), ("number", True), ("number", 0),
            ("title", ""), ("body", []), ("state", "resolved"),
            ("updated_at", "not-a-date"), ("updated_at", "2026-01-01T00:00:00Z"),
            ("updated_at", "2026-07-01T12:00:00"), ("updated_at", "9999-12-31T00:00:00Z"),
        ]
        for key, value in bad_values:
            with self.subTest(key=key, value=value):
                payload = issue_payload()
                payload["issue"][key] = value
                with self.assertRaises(ValueError):
                    ingest(payload, self.root)
        for payload in ([], {}, {**issue_payload(), "action": "closed"}):
            with self.assertRaises(ValueError):
                ingest(payload, self.root)
        self.assertEqual({path.name for path in self.root.iterdir()}, {"contradiction_matrix.json"})

    def test_pr_and_invalid_repository_are_rejected(self) -> None:
        payload = issue_payload()
        payload["issue"]["pull_request"] = {}
        with self.assertRaises(ValueError):
            ingest(payload, self.root)
        payload = issue_payload()
        payload["repository"]["full_name"] = "../../elsewhere"
        with self.assertRaises(ValueError):
            ingest(payload, self.root)

    def test_replay_repairs_trace_after_interrupted_write(self) -> None:
        with patch("kernel.experience_event.append_trace_event", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                ingest(issue_payload(), self.root)
        result = ingest(issue_payload(), self.root)
        self.assertFalse(result["created"])
        self.assertTrue(result["trace_appended"])
        self.assertEqual(len(parse_jsonl("trace_ledger.jsonl", self.root)), 1)

    def test_corrupt_ledger_prevents_record_creation(self) -> None:
        (self.root / "trace_ledger.jsonl").write_text("not json\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            ingest(issue_payload(), self.root)
        self.assertFalse((self.root / "wounds").exists())

    def test_changed_matrix_does_not_reclassify_a_recorded_revision(self) -> None:
        result = ingest(issue_payload(), self.root)
        original = (self.root / result["path"]).read_bytes()
        matrix = self.root / "contradiction_matrix.json"
        matrix.write_text(matrix.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        replay = ingest(issue_payload(), self.root)
        self.assertFalse(replay["trace_appended"])
        self.assertEqual(original, (self.root / result["path"]).read_bytes())

    def test_tampered_record_cannot_be_blessed_by_another_trace(self) -> None:
        result = ingest(issue_payload(), self.root)
        event = self.read_event(result)
        event["possible_wounds"] = ["invented-intent"]
        (self.root / result["path"]).write_text(json.dumps(event), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "recorded trace hash"):
            ingest(issue_payload(), self.root)
        self.assertEqual(len(parse_jsonl("trace_ledger.jsonl", self.root)), 1)

    def test_repository_names_distinguish_equal_issue_numbers(self) -> None:
        first = ingest(issue_payload(), self.root)
        second_payload = issue_payload()
        second_payload["repository"]["full_name"] = "another/ctr"
        second = ingest(second_payload, self.root)
        self.assertNotEqual(first["path"], second["path"])

    def test_cli_reads_event_file_and_emits_only_safe_workflow_outputs(self) -> None:
        payload = issue_payload()
        body = '$(touch injected)\npath=../../escape\n${{ secrets.GITHUB_TOKEN }}'
        payload["issue"]["body"] = body
        event_file = self.root / "payload.json"
        event_file.write_text(json.dumps(payload), encoding="utf-8")
        output_file = self.root / "outputs.txt"
        env = {**os.environ, "GITHUB_EVENT_PATH": str(event_file), "GITHUB_OUTPUT": str(output_file)}
        completed = subprocess.run(
            [sys.executable, str(ROOT / "kernel/experience_event.py"), "--root", str(self.root)],
            env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(self.read_event(result)["source"]["body"], body)
        self.assertNotIn(body, completed.stdout)
        self.assertEqual(len(output_file.read_text().splitlines()), 3)
        self.assertFalse((self.root / "injected").exists())

    def test_cli_manual_snapshot_and_bad_json_exit_code(self) -> None:
        issue_file = self.root / "issue.json"
        issue_file.write_text(json.dumps(issue_payload()["issue"]), encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if key not in ("GITHUB_OUTPUT", "GITHUB_EVENT_PATH")}
        command = [sys.executable, str(ROOT / "kernel/experience_event.py"), "--root", str(self.root),
                   "--issue-file", str(issue_file), "--repository", "example/ctr"]
        completed = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.read_event(json.loads(completed.stdout))["source"]["action"], "snapshot")
        issue_file.write_text("{invalid", encoding="utf-8")
        failed = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1)
        self.assertNotIn("Traceback", failed.stderr)


if __name__ == "__main__":
    unittest.main()
