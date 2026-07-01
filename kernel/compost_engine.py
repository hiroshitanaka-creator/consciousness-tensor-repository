from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.ledger import append_trace_event, sha256_text
from kernel.repository import ROOT, write_json


ARTIFACT_RE = re.compile(r"^\s*-\s+artifact:\s*(?P<artifact>.+?)\s*$", re.MULTILINE)


def _extract_block(text: str, start: int) -> str:
    next_match = ARTIFACT_RE.search(text, start + 1)
    return text[start : next_match.start() if next_match else len(text)]


def _field(block: str, name: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(name)}:\s*(.+?)\s*$", block, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def relation_artifacts(root: Path = ROOT) -> list[dict[str, object]]:
    path = root / "relation_graph.yaml"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    artifacts: list[dict[str, object]] = []
    for match in ARTIFACT_RE.finditer(text):
        block = _extract_block(text, match.start())
        artifacts.append(
            {
                "artifact": match.group("artifact").strip(),
                "created_at": _field(block, "created_at"),
                "ttl_days": int(_field(block, "ttl_days") or 0),
                "compost_target": _field(block, "compost_target"),
                "compost_after_inactivity": (_field(block, "compost_after_inactivity") or "false").lower() == "true",
            }
        )
    return artifacts


def scan(root: Path = ROOT) -> dict[str, object]:
    today = date.today()
    expired: list[dict[str, object]] = []
    watched = relation_artifacts(root)
    for item in watched:
        created_at = item.get("created_at")
        ttl_days = int(item.get("ttl_days") or 0)
        if not created_at or ttl_days <= 0:
            continue
        try:
            created = datetime.strptime(str(created_at), "%Y-%m-%d").date()
        except ValueError:
            continue
        age_days = (today - created).days
        if age_days >= ttl_days:
            expired.append({**item, "age_days": age_days})
    plan = {
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "watched_artifacts": watched,
        "expired_artifacts": expired,
        "apply_required_env": "CTR_APPLY_COMPOST=1",
    }
    write_json(".ctr/compost_plan.json", plan, root)
    return plan


def move(root: Path = ROOT) -> int:
    plan = scan(root)
    expired = plan["expired_artifacts"]
    if os.environ.get("CTR_APPLY_COMPOST") != "1":
        print(json.dumps({**plan, "dry_run": True}, indent=2, sort_keys=True))
        return 0

    moved: list[dict[str, str]] = []
    for item in expired:
        source = root / str(item["artifact"])
        target_value = item.get("compost_target")
        if not target_value or not source.exists() or not source.is_file():
            continue
        target = root / str(target_value)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        moved.append({"from": source.as_posix(), "to": target.as_posix()})

    append_trace_event(
        {
            "event": "compost_move",
            "model": "deterministic-stdlib",
            "prompt_hash": sha256_text(json.dumps(plan, sort_keys=True)),
            "input_sources": ["relation_graph.yaml"],
            "output_hash": sha256_text(json.dumps(moved, sort_keys=True)),
            "bias_risks": ["over-deletion", "historical amnesia"],
        },
        root,
    )
    print(json.dumps({"moved": moved}, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["scan", "move"])
    args = parser.parse_args()
    if args.command == "scan":
        print(json.dumps(scan(), indent=2, sort_keys=True))
        return 0
    return move()


if __name__ == "__main__":
    raise SystemExit(main())
