from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from kernel.context_graph import export_context, retrieve
from kernel.context_store import AXES, ContextStore, digest, make_record
from kernel.experimental_dream import dream, propose_dream, review_dream
from kernel.experiment_runner import experiment, git
from kernel.judge_assessment import assess
from kernel.repository import ROOT
from kernel.wound_lifecycle import ingest_experience, record_decision, transition


def run_demo(output):
    output = Path(output).resolve()
    if (output / "context/state.json").exists():
        raise ValueError("Choose a fresh demo output directory")
    store = ContextStore(output / "context")
    store.init("synthetic-demo", synthetic=True)
    actor = {"type": "system", "id": "synthetic-demo"}
    source = {"action": "opened", "repository": {"full_name": "example/synthetic"},
              "issue": {"number": 1, "title": "Memory retention", "body": "Keep only useful memory.",
                        "state": "open", "created_at": "2026-09-01T00:00:00Z", "updated_at": "2026-09-01T00:00:00Z"}}
    ingest_experience(store, source)
    wound = "wound:minimality-vs-ecology"
    for identifier, body in [("memory:essential", "Retention must not exceed 90 days."),
                             ("memory:redundant", "A duplicate note without additional requirements.")]:
        store.add(make_record(identifier, "memory", identifier, body, ["fixture:retention"], actor,
                              tags=["memory", "retention"], read_when=["choose a retention policy"]))
    generated = dream(store, wound, seed=42)
    hypothesis = propose_dream(store, {
        "title": "Synthetic forgetting hypothesis", "question": "Can the redundant memory be omitted?",
        "experiment": "Run the same test suite with and without the redundant memory.",
        "acceptance_criterion": "Both trials pass and the second reads fewer bytes.",
        "experiment_kind": "forgetting", "wound": wound, "source_ids": [wound, "memory:redundant"],
        "actor": actor, "generation": {"provider": "fixture", "model": "none", "prompt_hash": digest("synthetic prompt")}})
    with tempfile.TemporaryDirectory(prefix="ctr-demo-repo-") as directory:
        repo = Path(directory) / "repo"
        shutil.copytree(ROOT / "examples/evolution/trial_project", repo)
        git(repo, "init")
        git(repo, "add", ".")
        git(repo, "-c", "user.name=CTR Demo", "-c", "user.email=ctr-demo@example.invalid", "commit", "-m", "Synthetic trial")
        base = {"title": "Synthetic retention comparison", "acceptance": "Required variants preserve the retention contract.",
                "context_ids": ["memory:essential", "memory:redundant"], "wounds": [wound], "timeout_seconds": 15}
        comparison = experiment(store, repo, {**base, "kind": "counterfactual", "required_pass": ["baseline"],
            "variants": [{"name": "baseline", "ref": "HEAD"},
                         {"name": "unbounded", "ref": "HEAD", "edits": {"policy.json": '{"retention_days":365}'}}]}, trust_code=True)
        forgetting_plan = {**base, "kind": "forgetting", "hypothesis": hypothesis,
            "variants": [{"name": "baseline", "ref": "HEAD"}, {"name": "reduced", "ref": "HEAD", "omit": ["memory:redundant"]}]}
        forgetting = experiment(store, repo, forgetting_plan, trust_code=True)
        essential = experiment(store, repo, {**forgetting_plan,
            "variants": [{"name": "baseline", "ref": "HEAD"}, {"name": "missing-essential", "ref": "HEAD", "omit": ["memory:essential"]}]}, trust_code=True)
    evaluation = assess(store, ROOT, json.loads((ROOT / "examples/evolution/judge_corpus.json").read_text()), trust_code=True)
    decision = record_decision(store, {
        "id": "decision:synthetic-retention", "title": "Retain essential context", "choice": "Use bounded context and retain the essential record.",
        "alternatives": ["Retain every duplicate.", "Omit the essential retention rule."],
        "cost": "Future tasks might require revisiting omitted information.", "failure_condition": "A required test fails after omission.",
        "evidence": [forgetting], "sources": ["fixture:retention"], "actor": actor, "axes": {axis: False for axis in AXES}}, accept=True)
    transition(store, wound, "investigating")
    transition(store, wound, "scarred", decision=decision, evidence=forgetting)
    review_dream(store, hypothesis, "accepted", decision)
    source["action"] = "edited"
    source["issue"]["updated_at"] = "2026-09-02T00:00:00Z"
    ingest_experience(store, source)
    result = retrieve(store, "retention", budget=16000)
    export_context(store)
    records = store.load()["records"]
    summary = {
        "synthetic": True,
        "wound_recurs": records[wound]["status"] == "recurring",
        "comparison_detected_failure": [v["passed"] for v in records[comparison]["data"]["variants"]] == [True, False],
        "redundant_forgetting_passed": records[forgetting]["data"]["success"],
        "essential_forgetting_failed": not records[essential]["data"]["success"],
        "dream_assimilated_with_evidence": records[hypothesis]["status"] == "accepted",
        "template_dream_quarantined": records[generated]["status"] == "proposed",
        "all_axes_assessed": records[evaluation]["data"]["success"],
        "retrieved_context": bool(result["selected"]),
        "records": len(records), "graph": str(output / "context/graph.json")}
    if not all(v for k, v in summary.items() if k not in {"records", "graph"}):
        raise ValueError("End-to-end demo failed: " + json.dumps(summary))
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_demo(args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
