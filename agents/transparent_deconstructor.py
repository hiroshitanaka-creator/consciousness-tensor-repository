from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.repository import AxisReport, ROOT, has_all_text, parse_jsonl, write_axis_report


REQUIRED_TRACE_FIELDS = [
    "timestamp",
    "event",
    "model",
    "prompt_hash",
    "input_sources",
    "output_hash",
    "rejected_outputs",
    "commercial_dependency",
    "bias_risks",
]


def _audit_dreams() -> list[str]:
    demands: list[str] = []
    for path in sorted((ROOT / "dreams" / "pending").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for section in ["Source residues", "Shadow hypothesis", "Forbidden design impulse", "Counter-ritual"]:
            if f"## {section}" not in text:
                demands.append(f"{path.as_posix()} missing ## {section}.")
    return demands


def evaluate(pr: str | None = None, include_dreams: bool = False) -> AxisReport:
    demands: list[str] = []
    evidence: dict[str, object] = {"pr": pr}
    try:
        records = parse_jsonl("trace_ledger.jsonl", ROOT)
    except ValueError as exc:
        records = []
        demands.append(str(exc))
    evidence["trace_event_count"] = len(records)
    if not records:
        demands.append("trace_ledger.jsonl needs at least one event.")

    for index, record in enumerate(records, start=1):
        for field in REQUIRED_TRACE_FIELDS:
            if field not in record:
                demands.append(f"trace_ledger.jsonl line {index} missing {field}.")
        if not record.get("input_sources"):
            demands.append(f"trace_ledger.jsonl line {index} needs input_sources.")
        if not record.get("commercial_dependency"):
            demands.append(f"trace_ledger.jsonl line {index} needs commercial_dependency.")
        if not record.get("bias_risks"):
            demands.append(f"trace_ledger.jsonl line {index} needs bias_risks.")

    bias_path = ROOT / "bias_manifest.yaml"
    if not bias_path.exists():
        demands.append("Create bias_manifest.yaml.")
        bias_text = ""
    else:
        bias_text = bias_path.read_text(encoding="utf-8")
    missing_bias_terms = has_all_text(bias_text, ["commercial_dependency", "bias_risks", "mitigations", "marketing_restrictions"])
    for term in missing_bias_terms:
        demands.append(f"bias_manifest.yaml must disclose {term}.")

    consciousness_text = (ROOT / "CONSCIOUSNESS.md").read_text(encoding="utf-8")
    missing_protocol_terms = has_all_text(
        consciousness_text,
        ["does not claim phenomenal consciousness", "Forbidden Claims", "Merge Law"],
    )
    for term in missing_protocol_terms:
        demands.append(f"CONSCIOUSNESS.md must include {term}.")

    if include_dreams:
        demands.extend(_audit_dreams())

    score = max(0.0, 1.0 - (len(demands) * 0.15))
    return AxisReport(axis="transparency", score=score, veto=bool(demands), demands=demands, evidence=evidence)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", default=None)
    parser.add_argument("command", nargs="?", default="audit", choices=["audit", "audit-dreams"])
    args = parser.parse_args()
    report = evaluate(args.pr, include_dreams=args.command == "audit-dreams")
    write_axis_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
