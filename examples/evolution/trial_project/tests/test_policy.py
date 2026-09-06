import json
import os
import unittest
from pathlib import Path


class RetentionContract(unittest.TestCase):
    def test_retention_limit(self):
        policy = json.loads(Path("policy.json").read_text())
        self.assertLessEqual(policy["retention_days"], 90)

    def test_essential_context(self):
        snapshot = json.loads(Path(os.environ["CTR_EXPERIMENT_CONTEXT"]).read_text())
        self.assertEqual(snapshot.get("memory:essential", {}).get("body"), "Retention must not exceed 90 days.")
