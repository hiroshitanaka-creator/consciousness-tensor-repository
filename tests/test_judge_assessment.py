import json
import tempfile
import unittest
from pathlib import Path

from kernel.context_store import AXES, ContextStore
from kernel.judge_assessment import assess
from kernel.repository import ROOT


class JudgeAssessmentTests(unittest.TestCase):
    def test_actual_agents_against_labeled_positive_and_negative_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ContextStore(Path(directory) / "context")
            store.init("fixture", synthetic=True)
            corpus = json.loads((ROOT / "examples/evolution/judge_corpus.json").read_text())
            identifier = assess(store, ROOT, corpus, trust_code=True)
            record = store.load()["records"][identifier]
            self.assertTrue(record["data"]["success"], record["data"]["axes"])
            for axis in AXES:
                self.assertGreater(record["data"]["axes"][axis]["true_veto"], 0)
                self.assertGreater(record["data"]["axes"][axis]["true_pass"], 0)
                self.assertEqual(record["data"]["axes"][axis]["miss_rate"], 0)
            before = store.path.read_bytes()
            self.assertEqual(assess(store, ROOT, corpus, trust_code=True), identifier)
            self.assertEqual(before, store.path.read_bytes())
            bad = {"ref": "HEAD", "label_source": "fixture", "cases": [{"name": "bad"}, {"name": "bad2"}]}
            with self.assertRaises(ValueError):
                assess(store, ROOT, bad, trust_code=True)
