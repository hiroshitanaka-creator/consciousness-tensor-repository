from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.repository import AxisReport, ROOT, list_repo_files, parse_jsonl, relative, write_axis_report


FORBIDDEN_SELF_ASSERTIONS = [
    "i am sentient",
    "i feel",
    "i have a soul",
    "i am your companion",
    "i optimize user satisfaction",
]


def _duplicate_file_hashes(files: list[Path]) -> list[str]:
    import hashlib

    seen: Counter[str] = Counter()
    paths_by_hash: dict[str, list[str]] = {}
    for path in files:
        if path.name == ".gitkeep":
            continue
        if path.is_file() and path.stat().st_size > 0:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            seen[digest] += 1
            paths_by_hash.setdefault(digest, []).append(relative(path))
    duplicates: list[str] = []
    for digest, count in seen.items():
        if count > 1:
            duplicates.extend(paths_by_hash[digest])
    return duplicates


def evaluate(pr: str | None = None) -> AxisReport:
    demands: list[str] = []
    evidence: dict[str, object] = {"pr": pr}
    files = list_repo_files(ROOT)
    python_files = [path for path in files if path.suffix == ".py"]
    evidence["tracked_file_count"] = len(files)
    evidence["python_file_count"] = len(python_files)

    entropy_path = ROOT / "entropy_budget.json"
    if not entropy_path.exists():
        demands.append("Create entropy_budget.json.")
        entropy = {}
    else:
        entropy = json.loads(entropy_path.read_text(encoding="utf-8"))
    if entropy.get("deletions_required_per_pr") is not True:
        demands.append("entropy_budget.json must require deletion, compression, or simplification per PR.")

    max_lines = int(entropy.get("max_python_file_lines", 350) or 350)
    oversized = []
    for path in python_files:
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > max_lines:
            oversized.append(f"{relative(path)}:{line_count}")
    evidence["oversized_python_files"] = oversized
    if oversized:
        demands.append(f"Compress Python files above {max_lines} lines: {', '.join(oversized)}")

    duplicates = _duplicate_file_hashes(files)
    evidence["duplicate_files"] = duplicates
    if duplicates:
        demands.append("Remove or justify duplicate file contents: " + ", ".join(duplicates[:10]))

    self_text = (ROOT / "SELF.md").read_text(encoding="utf-8").lower() if (ROOT / "SELF.md").exists() else ""
    active_part = self_text.split("## claims deleted since last cycle", 1)[0]
    bad_assertions = [item for item in FORBIDDEN_SELF_ASSERTIONS if item in active_part]
    evidence["forbidden_self_assertions"] = bad_assertions
    if bad_assertions:
        demands.append("Delete personality-like active self assertions from SELF.md.")

    try:
        trace_records = parse_jsonl("trace_ledger.jsonl", ROOT)
    except ValueError as exc:
        trace_records = []
        demands.append(str(exc))
    evidence["trace_event_count"] = len(trace_records)
    if len(trace_records) == 0:
        demands.append("Keep at least one trace ledger event.")

    score = max(0.0, 1.0 - (len(demands) * 0.2))
    return AxisReport(axis="null", score=score, veto=bool(demands), demands=demands, evidence=evidence)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", default=None)
    parser.add_argument("command", nargs="?", default="audit", choices=["audit", "audit-compost"])
    args = parser.parse_args()
    report = evaluate(args.pr)
    write_axis_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
