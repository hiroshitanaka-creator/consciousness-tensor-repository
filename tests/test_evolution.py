import copy
import json
import tempfile
import unittest
from pathlib import Path

from kernel.context_graph import export_context, retrieve
from kernel.context_store import ContextStore, digest
from kernel.experimental_dream import dream, propose_dream, review_dream
from kernel.experiment_runner import experiment, validate_manifest
from kernel.wound_lifecycle import compost_record, ingest_experience, record_decision, transition
from tests.context_helpers import WOUND, decision, git, manifest, memory, payload, trial_repo


class EvolutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ContextStore(self.root / "context")
        self.store.init("fixture", synthetic=True)
        ingest_experience(self.store, payload())
        self.store.add(memory())
        self.store.add(memory("memory:redundant", "A duplicated observation with no additional constraints."))
        self.repo = trial_repo(self.root)

    def run_plan(self, kind):
        identifier = experiment(self.store, self.repo, manifest(kind), trust_code=True)
        return identifier, self.store.load()["records"][identifier]

    def test_counterfactual_compares_rejected_design_without_touching_original(self):
        before = git(self.repo, "status", "--porcelain")
        identifier, record = self.run_plan("counterfactual")
        self.assertEqual([r["passed"] for r in record["data"]["variants"]], [True, False])
        self.assertTrue(record["data"]["success"])
        self.assertEqual(git(self.repo, "status", "--porcelain"), before)
        self.assertEqual(json.loads((self.repo / "policy.json").read_text())["retention_days"], 90)
        self.assertEqual(git(self.repo, "worktree", "list", "--porcelain").count("worktree "), 1)
        self.assertEqual(experiment(self.store, self.repo, manifest(), trust_code=True), identifier)

    def test_forgetting_removes_redundant_context_without_modifying_memory(self):
        before = copy.deepcopy(self.store.load()["records"]["memory:redundant"])
        identifier, record = self.run_plan("forgetting")
        self.assertTrue(record["data"]["success"])
        baseline, reduced = record["data"]["variants"]
        self.assertLess(reduced["context_bytes"], baseline["context_bytes"])
        self.assertEqual(self.store.load()["records"]["memory:redundant"], before)

    def test_forgetting_essential_memory_fails_and_does_not_delete_it(self):
        plan = manifest("forgetting")
        plan["variants"][1]["omit"] = ["memory:essential"]
        identifier = experiment(self.store, self.repo, plan, trust_code=True)
        record = self.store.load()["records"][identifier]
        self.assertFalse(record["data"]["success"])
        self.assertIn("memory:essential", self.store.load()["records"])

    def test_wound_scar_requires_linked_success_and_reopens_on_new_evidence(self):
        proof, _ = self.run_plan("forgetting")
        choice = record_decision(self.store, decision(proof), accept=True)
        transition(self.store, WOUND, "investigating")
        transition(self.store, WOUND, "scarred", decision=choice, evidence=proof)
        self.assertEqual(self.store.load()["records"][WOUND]["status"], "scarred")
        ingest_experience(self.store, payload("edited", "2026-09-02T12:00:00Z"))
        wound = self.store.load()["records"][WOUND]
        self.assertEqual(wound["status"], "recurring")
        self.assertEqual(wound["data"]["recurrences"], 1)
        export_context(self.store)
        self.assertIn(choice, json.loads((self.store.root / "SELF.json").read_text())["accepted_decisions"])

    def test_old_unseen_observation_does_not_create_false_recurrence(self):
        ingest_experience(self.store, payload("edited", "2026-09-03T12:00:00Z"))
        proof, _ = self.run_plan("forgetting")
        choice = record_decision(self.store, decision(proof), accept=True)
        transition(self.store, WOUND, "investigating")
        transition(self.store, WOUND, "scarred", decision=choice, evidence=proof)
        ingest_experience(self.store, payload("edited", "2026-09-02T12:00:00Z"))
        self.assertEqual(self.store.load()["records"][WOUND]["status"], "scarred")

    def test_dream_is_source_based_repeatable_and_requires_evidence_for_assimilation(self):
        identifier = dream(self.store, WOUND, seed=42)
        self.assertEqual(identifier, dream(self.store, WOUND, seed=42))
        hypothesis = self.store.load()["records"][identifier]
        self.assertEqual(hypothesis["status"], "proposed")
        self.assertIn("acceptance_criterion", hypothesis["data"])
        with self.assertRaises(ValueError):
            review_dream(self.store, identifier, "accepted", "decision:missing")
        identifier = propose_dream(self.store, {
            "title": "Bounded forgetting", "question": "Is the redundant memory necessary?",
            "experiment": "Run the same suite with that memory omitted.",
            "acceptance_criterion": "Both trials pass with fewer context bytes.",
            "experiment_kind": "forgetting", "wound": WOUND, "source_ids": [WOUND],
            "actor": {"type": "assistant", "id": "fixture-agent"},
            "generation": {"provider": "fixture", "model": "fixture", "prompt_hash": digest("fixture prompt")}})
        plan = manifest("forgetting")
        plan["hypothesis"] = identifier
        proof = experiment(self.store, self.repo, plan, trust_code=True)
        choice = record_decision(self.store, decision(proof), accept=True)
        review_dream(self.store, identifier, "accepted", choice)
        self.assertEqual(self.store.load()["records"][identifier]["status"], "accepted")
        self.assertFalse(self.store.load()["records"][identifier]["data"]["main_merge_allowed"])

    def test_every_veto_is_independent_and_actor_stays_assistant(self):
        proof, _ = self.run_plan("forgetting")
        for axis in decision(proof)["axes"]:
            proposal = decision(proof)
            proposal["axes"][axis] = True
            with self.assertRaises(ValueError):
                record_decision(self.store, proposal, accept=True)
        identifier = record_decision(self.store, decision(proof), accept=True)
        self.assertEqual(self.store.load()["records"][identifier]["actor"]["type"], "assistant")

    def test_compost_retains_record_but_excludes_it_from_active_search(self):
        proof, _ = self.run_plan("forgetting")
        choice = record_decision(self.store, decision(proof), accept=True)
        compost_record(self.store, "memory:redundant", choice)
        active = {x["record"]["id"] for x in retrieve(self.store, "retention", budget=32000)["selected"]}
        self.assertNotIn("memory:redundant", active)
        self.assertIn("memory:redundant", self.store.load()["records"])

    def test_experiment_boundaries_and_protected_rules(self):
        with self.assertRaises(ValueError):
            experiment(self.store, self.repo, manifest())
        invalid = manifest("forgetting")
        invalid["variants"][1]["omit"] = ["rule:ctr-protocol"]
        with self.assertRaises(ValueError):
            experiment(self.store, self.repo, invalid, trust_code=True)
        invalid = manifest()
        invalid["timeout_seconds"] = 1000
        with self.assertRaises(ValueError):
            validate_manifest(invalid, "counterfactual")
        invalid = manifest()
        invalid["variants"][1]["edits"] = {"../escape.json": "bad"}
        with self.assertRaises(ValueError):
            experiment(self.store, self.repo, invalid, trust_code=True)
        self.assertFalse((self.root / "escape.json").exists())

    def test_missing_decision_and_invalid_transitions_fail_without_mutation(self):
        before = self.store.path.read_bytes()
        with self.assertRaises(ValueError):
            transition(self.store, WOUND, "scarred")
        with self.assertRaises(ValueError):
            record_decision(self.store, decision("experiment:missing"), accept=True)
        self.assertEqual(before, self.store.path.read_bytes())
