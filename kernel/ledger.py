from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kernel.repository import ROOT, list_repo_files, relative


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def repo_tree_hash(root: Path = ROOT) -> str:
    digest = hashlib.sha256()
    for path in list_repo_files(root):
        rel = relative(path, root)
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def append_trace_event(event: dict[str, Any], root: Path = ROOT) -> Path:
    path = root / "trace_ledger.jsonl"
    enriched = {
        "timestamp": event.get("timestamp", now_iso()),
        "event": event["event"],
        "model": event.get("model", "none"),
        "prompt_hash": event.get("prompt_hash", sha256_text("no prompt")),
        "input_sources": event.get("input_sources", []),
        "output_hash": event.get("output_hash", sha256_text(json.dumps(event, sort_keys=True))),
        "rejected_outputs": event.get("rejected_outputs", []),
        "commercial_dependency": event.get("commercial_dependency", ["GitHub platform"]),
        "bias_risks": event.get("bias_risks", ["automation bias"]),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(enriched, sort_keys=True) + "\n")
    return path
