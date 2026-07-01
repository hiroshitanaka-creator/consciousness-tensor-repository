from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.contradiction_engine import extract_active_contradictions
from kernel.repository import ROOT, load_axis_reports, write_json


AXES = [
    ("null", "agents/null_auditor.py"),
    ("existential", "agents/existential_destroyer.py"),
    ("fudo", "agents/fudo_compiler.py"),
    ("shadow", "agents/abyss_shadow.py"),
    ("transparency", "agents/transparent_deconstructor.py"),
]


def run_all_agents(pr_number: str | None = None, root: Path = ROOT) -> int:
    for _axis, script in AXES:
        command = [sys.executable, script]
        if pr_number:
            command.extend(["--pr", pr_number])
        completed = subprocess.run(command, cwd=root)
        if completed.returncode != 0:
            return completed.returncode
    return 0


def tensorize_without_compromise(root: Path = ROOT) -> dict[str, object]:
    reports = load_axis_reports(root)
    missing = [axis for axis, _script in AXES if axis not in reports]
    if missing:
        raise RuntimeError(f"Missing axis reports: {', '.join(missing)}")
    merge_allowed = not any(bool(report.get("veto")) for report in reports.values())
    tensor_report = {
        "merge_allowed": merge_allowed,
        "required_transformations": {
            axis: reports[axis].get("demands", [])
            for axis, _script in AXES
        },
        "axis_scores": {
            axis: reports[axis].get("score")
            for axis, _script in AXES
        },
        "contradictions_preserved": extract_active_contradictions(root),
        "reports": reports,
    }
    write_json(".ctr/tensor_report.json", tensor_report, root)
    return tensor_report


def print_summary(tensor_report: dict[str, object]) -> None:
    print(json.dumps(tensor_report, indent=2, sort_keys=True))
    if tensor_report["merge_allowed"]:
        print("Tensor gate passed: no axis used its veto.")
        return
    print("Tensor gate blocked: at least one axis used its veto.")
    transformations = tensor_report["required_transformations"]
    for axis, demands in transformations.items():
        if demands:
            print(f"[{axis}]")
            for demand in demands:
                print(f"- {demand}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Run all axis agents before tensorizing.")
    parser.add_argument("--pr", default=None, help="Optional pull request number for report metadata.")
    parser.add_argument("--enforce", action="store_true", help="Exit non-zero if any axis vetoes.")
    args = parser.parse_args()

    if args.all:
        code = run_all_agents(args.pr)
        if code:
            return code

    try:
        tensor_report = tensorize_without_compromise()
    except RuntimeError as exc:
        print(str(exc))
        return 2

    print_summary(tensor_report)
    if args.enforce and not tensor_report["merge_allowed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
