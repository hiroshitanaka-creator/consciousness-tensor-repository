import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernel.context_graph import export_context, link_records, retrieve
from kernel.context_store import ContextStore, digest, filename
from kernel.wound_lifecycle import ingest_experience
from tests.context_helpers import memory, payload


class ContextGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ContextStore(Path(self.temp.name) / "context")
        self.store.init("fixture", synthetic=True)

    def test_record_replay_and_atomic_failed_write(self):
        record = memory()
        self.store.add(record)
        before = self.store.path.read_bytes()
        self.store.add(record)
        self.assertEqual(before, self.store.path.read_bytes())
        with patch("kernel.context_store.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.store.add(memory("memory:new"))
        self.assertEqual(before, self.store.path.read_bytes())
        self.assertFalse((self.store.root / ".writer-lock").exists())

    def test_failed_mutation_does_not_commit_partial_state(self):
        before = self.store.path.read_bytes()
        def broken(records):
            records["memory:bad"] = {}
            raise ValueError("aborted")
        with self.assertRaises(ValueError):
            self.store.transact("test", {"type": "system", "id": "test"}, broken)
        self.assertEqual(before, self.store.path.read_bytes())

    def test_audit_detects_state_and_chain_tampering(self):
        self.store.add(memory())
        original = self.store.path.read_text()
        state = json.loads(original)
        state["records"]["memory:essential"]["body"] = "Unrecorded mutation"
        self.store.path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, "audit digest"):
            self.store.load()
        state = json.loads(original)
        state["audit"][0]["action"] = "forged"
        self.store.path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, "audit chain"):
            self.store.load()

    def test_query_reads_related_opposition_and_logs_exact_versions(self):
        self.store.add(memory())
        other = memory("memory:opposition", "Keeping all records may expose private data.")
        other.update(title="Privacy tradeoff", tags=["privacy"], read_when=["review exposure"])
        self.store.add(other)
        link_records(self.store, "memory:essential", "contradicts", "memory:opposition")
        result = retrieve(self.store, "retention", budget=5000)
        self.assertEqual({x["record"]["id"] for x in result["selected"]}, {"memory:essential", "memory:opposition"})
        self.assertIn("relation:contradicts", [x["reason"] for x in result["selected"]])
        trace = self.store.load()["audit"][-1]
        self.assertEqual(trace["action"], "context_retrieved")
        self.assertEqual(trace["details"]["references"][0]["hash"], result["selected"][0]["hash"])
        self.assertNotIn("query", trace["details"])

    def test_cycles_terminate_and_budget_does_not_truncate_records(self):
        for number in range(3):
            self.store.add(memory(f"memory:m{number}"))
        for number in range(3):
            link_records(self.store, f"memory:m{number}", "depends_on", f"memory:m{(number+1)%3}")
        small = retrieve(self.store, "retention", budget=256)
        self.assertEqual(small["selected"], [])
        self.assertEqual(len(small["excluded_by_budget"]), 3)
        large = retrieve(self.store, "retention", budget=12000)
        self.assertEqual(len(large["selected"]), 3)

    def test_superseded_record_excluded_and_new_record_findable(self):
        self.store.add(memory("memory:old"))
        self.store.add(memory("memory:new"))
        link_records(self.store, "memory:new", "supersedes", "memory:old")
        result = retrieve(self.store, "retention")
        self.assertEqual([x["record"]["id"] for x in result["selected"]], ["memory:new"])
        self.assertEqual(len(retrieve(self.store, "retention", include_inactive=True)["selected"]), 2)

    def test_japanese_retrieval_and_graph_projection(self):
        record = memory("memory:japanese", "\u8a18\u61b6\u306e\u4fdd\u5b58\u671f\u9593\u3092\u77ed\u304f\u3059\u308b")
        record["read_when"] = ["\u4fdd\u5b58\u671f\u9593\u306e\u5909\u66f4"]
        self.store.add(record)
        self.assertEqual(len(retrieve(self.store, "\u4fdd\u5b58\u671f\u9593")["selected"]), 1)
        export_context(self.store)
        self.assertTrue((self.store.root / "records" / filename(record["id"])).exists())
        self.assertIn(record["id"], (self.store.root / "INDEX.md").read_text())
        self.assertEqual(json.loads((self.store.root / "graph.json").read_text())["state_hash"],
                         digest(self.store.load()["records"]))

    def test_unknown_queries_and_invalid_graph_edges(self):
        self.store.add(memory())
        self.assertTrue(retrieve(self.store, "unrelatedword")["no_match"])
        with self.assertRaises(ValueError):
            link_records(self.store, "memory:essential", "supports", "memory:absent")

    def test_lock_and_public_personal_context_guard(self):
        with self.store.lock():
            with self.assertRaises(ValueError):
                self.store.add(memory())
        with patch.dict("os.environ", {"GITHUB_REPOSITORY_VISIBILITY": "public"}):
            with self.assertRaises(ValueError):
                ContextStore(Path(self.temp.name) / "private").init("person")

    def test_domain_record_injection_rejected(self):
        record = memory()
        record.update(kind="experiment", status="accepted")
        with self.assertRaises(ValueError):
            self.store.add(record)

    def test_experience_replay_preserves_wound_occurrences(self):
        first = ingest_experience(self.store, payload())
        before = self.store.path.read_bytes()
        self.assertTrue(ingest_experience(self.store, payload())["duplicate"])
        self.assertEqual(before, self.store.path.read_bytes())
        for name in first["wounds"]:
            self.assertEqual(len(self.store.load()["records"]["wound:" + name]["data"]["occurrences"]), 1)
