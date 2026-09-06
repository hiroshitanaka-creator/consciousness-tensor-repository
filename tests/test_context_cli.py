import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kernel.repository import ROOT
from tests.context_helpers import payload


class ContextCLITests(unittest.TestCase):
    def test_private_issue_to_graph_replay_and_new_process_retrieval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = root / "context"
            command = [sys.executable, "-m", "kernel.ctr", "--context", str(context)]
            def run(*args):
                return subprocess.run([*command, *args], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run("init", "--owner", "fixture", "--synthetic").returncode, 0)
            issue = root / "issue.json"
            issue.write_text(json.dumps(payload()), encoding="utf-8")
            observed = run("ingest", "--file", str(issue))
            self.assertEqual(observed.returncode, 0, observed.stderr)
            repeated = run("ingest", "--file", str(issue))
            self.assertTrue(json.loads(repeated.stdout)["duplicate"])
            result = run("search", "memory", "--budget", "16000")
            self.assertEqual(result.returncode, 0, result.stderr)
            selected = json.loads(result.stdout)["selected"]
            self.assertTrue(any(x["record"]["kind"] == "experience" for x in selected))
            self.assertTrue(any(x["record"]["kind"] == "wound" for x in selected))
            self.assertTrue((context / "INDEX.md").exists())
            self.assertTrue((context / "SELF.json").exists())
            self.assertEqual(run("verify").returncode, 0)
            invalid = root / "bad.json"
            invalid.write_text("{invalid")
            failed = run("record", "--file", str(invalid))
            self.assertNotEqual(failed.returncode, 0)
            self.assertNotIn("Traceback", failed.stderr)
