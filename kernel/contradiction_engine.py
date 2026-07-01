from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.repository import ROOT


def load_contradictions(root: Path = ROOT) -> list[dict[str, Any]]:
    path = root / "contradiction_matrix.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("contradictions", [])


def extract_active_contradictions(root: Path = ROOT) -> list[str]:
    return [
        item["id"]
        for item in load_contradictions(root)
        if item.get("preserved_tension") is True and "id" in item
    ]


def validate_contradictions(root: Path = ROOT) -> list[str]:
    demands: list[str] = []
    contradictions = load_contradictions(root)
    if not contradictions:
        return ["Add at least one preserved contradiction to contradiction_matrix.json."]
    for item in contradictions:
        if not item.get("id"):
            demands.append("Every contradiction needs an id.")
        if item.get("preserved_tension") is not True:
            demands.append(f"Contradiction {item.get('id', '<missing>')} must preserve tension.")
        if not item.get("resolution"):
            demands.append(f"Contradiction {item.get('id', '<missing>')} needs a resolution field.")
    return demands


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check", "list"], nargs="?", default="check")
    args = parser.parse_args()
    if args.command == "list":
        print(json.dumps(extract_active_contradictions(), indent=2))
        return 0
    demands = validate_contradictions()
    if demands:
        print(json.dumps({"ok": False, "demands": demands}, indent=2))
        return 1
    print(json.dumps({"ok": True, "contradictions": extract_active_contradictions()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
