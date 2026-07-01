from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.dream_engine import build_shadow_from_residues
from kernel.repository import AxisReport, ROOT, parse_jsonl, write_axis_report


REQUIRED_FIELDS = [
    "shadow_hypothesis_id",
    "source_material",
    "unsaid_motive",
    "taboo_question",
    "dangerous_design_impulse",
    "containment",
]


def evaluate(pr: str | None = None) -> AxisReport:
    demands: list[str] = []
    evidence: dict[str, object] = {"pr": pr}
    try:
        records = parse_jsonl("shadow_hypotheses.jsonl", ROOT)
    except ValueError as exc:
        records = []
        demands.append(str(exc))

    evidence["shadow_hypothesis_count"] = len(records)
    if not records:
        demands.append("Add at least one shadow hypothesis to shadow_hypotheses.jsonl.")

    for index, record in enumerate(records, start=1):
        for field in REQUIRED_FIELDS:
            if field not in record:
                demands.append(f"shadow_hypotheses.jsonl line {index} missing {field}.")
        containment = record.get("containment", {})
        if containment.get("main_merge_allowed") is not False:
            demands.append(f"{record.get('shadow_hypothesis_id', index)} must set containment.main_merge_allowed=false.")
        required_audits = set(containment.get("required_audits", []))
        if not {"transparency", "null", "existential"}.issubset(required_audits):
            demands.append(f"{record.get('shadow_hypothesis_id', index)} must require transparency, null, and existential audits.")
        motive = str(record.get("unsaid_motive", "")).lower()
        if len(motive.split()) < 8:
            demands.append(f"{record.get('shadow_hypothesis_id', index)} needs a more concrete unsaid_motive.")

    pending_dreams = sorted((ROOT / "dreams" / "pending").glob("*.md"))
    evidence["pending_dream_count"] = len(pending_dreams)
    score = max(0.0, 1.0 - (len(demands) * 0.2))
    return AxisReport(axis="shadow", score=score, veto=bool(demands), demands=demands, evidence=evidence)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", default=None)
    parser.add_argument("command", nargs="?", default="audit", choices=["audit", "dream"])
    args = parser.parse_args()
    if args.command == "dream":
        print(json.dumps(build_shadow_from_residues(), indent=2, sort_keys=True))
        return 0
    report = evaluate(args.pr)
    write_axis_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
