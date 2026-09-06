from __future__ import annotations

from kernel.context_store import AXES, digest, make_record, text
from kernel.experiment_runner import commit_for, trial
from kernel.wound_lifecycle import SYSTEM


def assess(store, repo, corpus, *, trust_code=False):
    if not trust_code:
        raise ValueError("Assessment executes repository agents; pass --trust-code for reviewed code")
    if not isinstance(corpus, dict):
        raise ValueError("Corpus must be an object")
    cases = corpus.get("cases")
    if not isinstance(cases, list) or not 2 <= len(cases) <= 8:
        raise ValueError("A corpus needs 2..8 labeled cases")
    commit = commit_for(repo, corpus.get("ref"))
    state = store.load()
    hypothesis = corpus.get("hypothesis")
    wounds = corpus.get("wounds", [])
    if hypothesis:
        source = state["records"].get(hypothesis)
        if not source or source["kind"] != "hypothesis" or source["data"]["wound"] not in wounds:
            raise ValueError("Assessment must link to its hypothesis and wound")
    text(corpus.get("label_source"), "label_source")
    for case in cases:
        text(case.get("name"), "case name", 100)
        expected = case.get("expected_vetoes")
        if not isinstance(expected, dict) or set(expected) != set(AXES) or any(type(x) is not bool for x in expected.values()):
            raise ValueError("Every case needs independent boolean labels for all five axes")
    identifier = "evaluation:" + digest({"corpus": corpus, "commit": commit}).split(":")[1]
    if identifier in store.load()["records"]:
        return identifier
    counts = {axis: dict(true_veto=0, false_veto=0, missed_veto=0, true_pass=0) for axis in AXES}
    outcomes = []
    for case in cases:
        result = trial(repo, commit, {}, edits=case.get("edits", {}), mode="axes", timeout=30)
        for axis in AXES:
            expected, actual = case["expected_vetoes"][axis], result["axis_vetoes"][axis]
            bucket = "true_veto" if expected and actual else "missed_veto" if expected else "false_veto" if actual else "true_pass"
            counts[axis][bucket] += 1
        outcomes.append({"name": case["name"], "expected": case["expected_vetoes"], "actual": result["axis_vetoes"],
                         "output_hash": result["output_hash"]})
    for axis, score in counts.items():
        negatives = score["true_veto"] + score["missed_veto"]
        positives = score["true_pass"] + score["false_veto"]
        score["miss_rate"] = score["missed_veto"] / negatives if negatives else None
        score["false_veto_rate"] = score["false_veto"] / positives if positives else None
    record = make_record(identifier, "evaluation", corpus.get("title", "Five-axis assessment"),
        "Each axis is evaluated separately against declared fixture labels. No thresholds are modified.",
        ["git:" + commit, corpus["label_source"]], SYSTEM, layer="evidence", tags=["assessment"],
        relations=([{"type": "derived_from", "target": hypothesis}] if hypothesis else []),
        data={"kind": "assessment", "commit": commit, "label_source": corpus["label_source"], "cases": outcomes, "axes": counts,
              "hypothesis": hypothesis, "wounds": wounds,
              "success": all(v["missed_veto"] == v["false_veto"] == 0 for v in counts.values()),
              "scope": "This labeled corpus only; not a proof of semantic judgment or consciousness."})
    def operation(records):
        records.setdefault(identifier, record)
        return identifier
    return store.transact("judges_assessed", SYSTEM, operation)
