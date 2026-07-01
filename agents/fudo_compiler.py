from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.compost_engine import relation_artifacts, scan
from kernel.repository import AxisReport, ROOT, write_axis_report


def evaluate(pr: str | None = None) -> AxisReport:
    demands: list[str] = []
    graph_path = ROOT / "relation_graph.yaml"
    evidence: dict[str, object] = {"pr": pr, "path": graph_path.as_posix()}
    if not graph_path.exists():
        return AxisReport("fudo", 0.0, True, ["Create relation_graph.yaml."], evidence)

    text = graph_path.read_text(encoding="utf-8")
    required_terms = ["humans:", "history:", "dependencies:", "ecological_cost:", "decay:", "ttl_days:", "compost_target:"]
    missing = [term for term in required_terms if term not in text]
    for term in missing:
        demands.append(f"relation_graph.yaml must include {term}")

    artifacts = relation_artifacts(ROOT)
    evidence["artifact_count"] = len(artifacts)
    if not artifacts:
        demands.append("relation_graph.yaml must define at least one artifact.")
    for item in artifacts:
        artifact = item["artifact"]
        if not item.get("ttl_days"):
            demands.append(f"{artifact} needs decay.ttl_days.")
        if not item.get("compost_target"):
            demands.append(f"{artifact} needs decay.compost_target.")
        if not re.search(rf"artifact:\s*{re.escape(str(artifact))}[\s\S]*?history:", text):
            demands.append(f"{artifact} needs a history relation.")

    plan = scan(ROOT)
    evidence["expired_artifacts"] = len(plan["expired_artifacts"])
    score = max(0.0, 1.0 - (len(demands) * 0.2))
    return AxisReport(axis="fudo", score=score, veto=bool(demands), demands=demands, evidence=evidence)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", default=None)
    parser.add_argument("command", nargs="?", default="audit", choices=["audit", "update-compost"])
    args = parser.parse_args()
    report = evaluate(args.pr)
    write_axis_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
