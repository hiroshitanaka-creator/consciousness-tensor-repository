import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernel.context_store import ContextStore, digest
from kernel.experimental_dream import propose_dream
from kernel.experiment_runner import child_env, edit_fixture
from kernel.private_cycle import main as private_cycle
from kernel.private_sync import resume_state
from kernel.scaffold_personal import scaffold
from kernel.wound_lifecycle import ingest_experience
from tests.context_helpers import WOUND, memory, payload


class EvolutionBoundaryTests(unittest.TestCase):
    def test_pending_pr_state_is_preserved_across_new_events(self):
        with tempfile.TemporaryDirectory() as directory:
            main = ContextStore(Path(directory) / "main")
            pending = ContextStore(Path(directory) / "pending")
            main.init("fixture", synthetic=True)
            pending.init("fixture", synthetic=True)
            pending.add(memory())
            self.assertTrue(resume_state(main, pending.load()))
            ingest_experience(main, payload())
            self.assertIn("memory:essential", main.load()["records"])
            self.assertFalse(resume_state(main, pending.load()))

    def test_divergent_pending_histories_are_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            main = ContextStore(Path(directory) / "main")
            pending = ContextStore(Path(directory) / "pending")
            main.init("fixture", synthetic=True)
            pending.init("fixture", synthetic=True)
            main.add(memory("memory:main"))
            pending.add(memory("memory:pending"))
            before = main.path.read_bytes()
            with self.assertRaises(ValueError):
                resume_state(main, pending.load())
            self.assertEqual(before, main.path.read_bytes())

    def test_trial_environment_does_not_forward_credentials(self):
        with patch.dict(os.environ, {"GH_TOKEN": "fixture", "OPENAI_API_KEY": "fixture", "SECRET_VALUE": "fixture"}):
            env = child_env(Path("snapshot.json"))
            self.assertNotIn("GH_TOKEN", env)
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("SECRET_VALUE", env)
            self.assertIn("CTR_EXPERIMENT_CONTEXT", env)

    def test_private_cycle_rejects_public_before_loading_data(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY_VISIBILITY": "public"}):
            with self.assertRaisesRegex(ValueError, "private"):
                private_cycle()

    def test_scaffold_is_pinned_idempotent_and_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "private"
            with self.assertRaises(ValueError):
                scaffold(root, "main")
            self.assertEqual(scaffold(root, "1" * 40), 4)
            workflow = root / ".github/workflows/context_cycle.yml"
            self.assertIn("1" * 40, workflow.read_text())
            self.assertNotIn("CTR_ENGINE_REVISION", workflow.read_text())
            self.assertEqual(scaffold(root, "1" * 40), 4)
            (root / "README.md").write_text("User-owned content")
            with self.assertRaises(ValueError):
                scaffold(root, "1" * 40)
            self.assertEqual((root / "README.md").read_text(), "User-owned content")

    def test_fixture_edits_cannot_change_executable_code_or_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("../escape.json", ".git/config", "tests/test_policy.py", "kernel/ctr.py"):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        edit_fixture(Path(directory), {name: "untrusted"})

    def test_external_proposal_records_source_versions_and_is_replayable(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ContextStore(Path(directory) / "context")
            store.init("fixture", synthetic=True)
            ingest_experience(store, payload())
            proposal = {"title": "External fixture", "question": "Can context be reduced?",
                        "experiment": "Run omission trials.", "acceptance_criterion": "All trials pass.",
                        "experiment_kind": "forgetting", "wound": WOUND, "source_ids": [WOUND],
                        "actor": {"type": "assistant", "id": "fixture-model"},
                        "generation": {"provider": "fixture", "model": "none", "prompt_hash": digest("fixture")}}
            with patch.dict(os.environ, {"CTR_PENDING_BRANCH": "dream/context-cycle"}):
                identifier = propose_dream(store, proposal)
            before = store.path.read_bytes()
            self.assertEqual(propose_dream(store, proposal), identifier)
            self.assertEqual(store.path.read_bytes(), before)
            record = store.load()["records"][identifier]
            self.assertEqual(record["status"], "proposed")
            self.assertEqual(record["data"]["branch"], "dream/context-cycle")
            self.assertEqual(record["data"]["branch_status"], "workflow-target")
            self.assertEqual(record["data"]["source_hashes"][WOUND], digest(store.load()["records"][WOUND]))
            proposal["generation"]["prompt_hash"] = "invalid"
            with self.assertRaises(ValueError):
                propose_dream(store, proposal)

    def test_inbox_record_requires_complete_time_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ContextStore(Path(directory) / "context")
            store.init("fixture", synthetic=True)
            record = memory()
            del record["review_after"]
            with self.assertRaises(ValueError):
                store.add(record)
