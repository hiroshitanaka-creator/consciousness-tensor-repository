from __future__ import annotations

import argparse
import re
from pathlib import Path

from kernel.context_store import ContextStore
from kernel.repository import ROOT


def scaffold(destination, revision):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Pin the engine to a reviewed 40-character commit SHA")
    destination = Path(destination).resolve()
    ContextStore(destination / "context")
    source = ROOT / "templates/personal-context"
    plan = {}
    for template in source.rglob("*"):
        if template.is_file():
            target = destination / template.relative_to(source)
            if target.is_symlink() or not target.resolve().is_relative_to(destination):
                raise ValueError("Template destination escapes the data repository")
            text = template.read_text(encoding="utf-8").replace("CTR_ENGINE_REVISION", revision)
            if target.exists() and target.read_text(encoding="utf-8") != text:
                raise ValueError("Refusing to overwrite an existing personal repository file: " + str(target))
            plan[target] = text
    for target, content in plan.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(content, encoding="utf-8", newline="\n")
    return len(plan)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--engine-ref", required=True)
    args = parser.parse_args()
    print(f"Prepared {scaffold(args.destination, args.engine_ref)} private repository starter files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
