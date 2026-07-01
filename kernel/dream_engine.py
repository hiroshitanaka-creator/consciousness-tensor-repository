from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.contradiction_engine import extract_active_contradictions
from kernel.ledger import append_trace_event, sha256_text
from kernel.repository import ROOT, ctr_dir, list_repo_files, relative, write_json


def gather_residues(root: Path = ROOT) -> dict[str, object]:
    residues: list[dict[str, str]] = []
    for path in list_repo_files(root):
        if path.suffix.lower() not in {".py", ".md", ".json", ".yaml", ".yml", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for index, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            if "todo" in lowered or "fixme" in lowered or "rejected" in lowered or "forbidden" in lowered:
                residues.append(
                    {
                        "path": relative(path, root),
                        "line": str(index),
                        "text": line.strip()[:220],
                    }
                )
    data = {
        "gathered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "contradictions": extract_active_contradictions(root),
        "residues": residues[:50],
    }
    write_json(".ctr/residues.json", data, root)
    return data


def build_shadow_from_residues(root: Path = ROOT) -> dict[str, object]:
    residues_path = ctr_dir(root) / "residues.json"
    residues = json.loads(residues_path.read_text(encoding="utf-8")) if residues_path.exists() else gather_residues(root)
    source_material = [
        f"{item['path']}:{item['line']}"
        for item in residues.get("residues", [])[:5]
    ] or ["contradiction_matrix.json"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hypothesis = {
        "shadow_hypothesis_id": f"shadow:{today}-generated",
        "source_material": source_material,
        "unsaid_motive": "The project may be using audit ritual to make ordinary maintenance feel metaphysically authorized.",
        "taboo_question": "Is the tensor gate preserving rigor, or making refusal feel profound?",
        "dangerous_design_impulse": "Automatically reject all changes that do not use the project's preferred vocabulary.",
        "containment": {
            "branch": f"dream/shadow-{today}-generated",
            "main_merge_allowed": False,
            "required_audits": ["transparency", "null", "existential"],
        },
    }
    write_json(".ctr/shadow_hypothesis.json", hypothesis, root)
    return hypothesis


def write_dream(root: Path = ROOT) -> Path:
    hypothesis_path = ctr_dir(root) / "shadow_hypothesis.json"
    hypothesis = (
        json.loads(hypothesis_path.read_text(encoding="utf-8"))
        if hypothesis_path.exists()
        else build_shadow_from_residues(root)
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dream_id = hypothesis["shadow_hypothesis_id"].split(":", 1)[1].replace(":", "-")
    target = root / "dreams" / "pending" / f"dream-{dream_id}.md"
    source_lines = "\n".join(f"- {item}" for item in hypothesis["source_material"])
    required = "\n".join(f"- {item}" for item in hypothesis["containment"]["required_audits"])
    content = f"""# Dream {today}

## Source residues

{source_lines}

## Dream image

The repository wants to become a judge but calls itself an experiment.

## Shadow hypothesis

{hypothesis["unsaid_motive"]}

## Taboo question

{hypothesis["taboo_question"]}

## Forbidden design impulse

{hypothesis["dangerous_design_impulse"]}

## Counter-ritual

Before assimilation, the dream must pass these audits:

{required}

## Required action

Open or update wound: transparency-vs-shadow.
"""
    target.write_text(content, encoding="utf-8")
    append_trace_event(
        {
            "event": "dream_written",
            "model": "deterministic-stdlib",
            "prompt_hash": sha256_text(json.dumps(hypothesis, sort_keys=True)),
            "input_sources": hypothesis["source_material"],
            "output_hash": sha256_text(content),
            "bias_risks": ["ritual language bias", "automation authority bias"],
        },
        root,
    )
    print(target.as_posix())
    return target


def open_pr(root: Path = ROOT) -> int:
    if os.environ.get("CTR_AUTO_PR") != "1":
        print("CTR_AUTO_PR is not 1; skipping branch, commit, push, and PR creation.")
        return 0

    branch = "dream/generated-shadow"
    commands = [
        ["git", "checkout", "-B", branch],
        ["git", "add", "dreams/pending", "trace_ledger.jsonl"],
        ["git", "commit", "-m", "Generate dream cycle artifact"],
        ["git", "push", "-u", "origin", branch],
        [
            "gh",
            "pr",
            "create",
            "--title",
            "Dream cycle artifact",
            "--body",
            "Generated by CTR dream cycle. Requires tensor gate review before assimilation.",
        ],
    ]
    for command in commands:
        completed = subprocess.run(command, cwd=root, text=True)
        if completed.returncode != 0:
            return completed.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["gather", "shadow", "write", "open-pr"])
    args = parser.parse_args()
    if args.command == "gather":
        print(json.dumps(gather_residues(), indent=2, sort_keys=True))
        return 0
    if args.command == "shadow":
        print(json.dumps(build_shadow_from_residues(), indent=2, sort_keys=True))
        return 0
    if args.command == "write":
        write_dream()
        return 0
    return open_pr()


if __name__ == "__main__":
    raise SystemExit(main())
