from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.decision_rite import check_decision_rite
from kernel.repository import AxisReport, ROOT, write_axis_report


def evaluate(pr: str | None = None) -> AxisReport:
    demands, evidence = check_decision_rite(ROOT / "rituals" / "decision_rite.md")
    evidence["pr"] = pr
    if "comfort" not in (ROOT / "CONSCIOUSNESS.md").read_text(encoding="utf-8").lower():
        demands.append("CONSCIOUSNESS.md must explicitly reject comfort as a merge substitute.")
    score = max(0.0, 1.0 - (len(demands) * 0.25))
    return AxisReport(axis="existential", score=score, veto=bool(demands), demands=demands, evidence=evidence)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", default=None)
    args = parser.parse_args()
    report = evaluate(args.pr)
    write_axis_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
