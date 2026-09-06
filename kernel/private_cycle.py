from __future__ import annotations

import json
import os
import re
from pathlib import Path

from kernel.context_graph import export_context
from kernel.context_store import ContextStore, read_json
from kernel.ctr import consume_inbox, main as cli
from kernel.experimental_dream import dream
from kernel.experiment_runner import experiment
from kernel.judge_assessment import assess
from kernel.repository import ROOT
from kernel.private_sync import restore_pending
from kernel.wound_lifecycle import ingest_experience


def main():
    if os.environ.get("GITHUB_REPOSITORY_VISIBILITY") != "private":
        raise ValueError("The private cycle only runs in a verified private data repository")
    path = Path(os.environ["CTR_DATA_DIR"])
    if cli(["--context", str(path), "init", "--owner", os.environ["GITHUB_REPOSITORY_OWNER"]]):
        raise ValueError("Context initialization failed")
    store = ContextStore(path)
    restore_pending(store, os.environ["GITHUB_REPOSITORY"], os.environ["CTR_PENDING_BRANCH"])
    if os.environ.get("GITHUB_EVENT_NAME") == "issues":
        ingest_experience(store, read_json(os.environ["GITHUB_EVENT_PATH"]))
    consume_inbox(store)
    operation = os.environ.get("CTR_OPERATION", "refresh")
    if operation == "dream":
        records = store.load()["records"]
        requested = os.environ.get("CTR_WOUND", "")
        wounds = [r["id"] for r in records.values() if r["kind"] == "wound" and r["status"] in {"unresolved", "recurring", "investigating"}]
        def last_dream(wound):
            return max((r["updated_at"] for r in records.values() if r["kind"] == "hypothesis" and r["data"]["wound"] == wound), default="")
        for wound in ([requested] if requested else sorted(wounds, key=last_dream)[:3]):
            dream(store, wound, seed=0)
    elif operation in {"experiment", "assess"}:
        name = os.environ.get("CTR_PLAN", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.json", name):
            raise ValueError("Select a JSON filename from plans/")
        plan = path.parent / "plans" / name
        if plan.is_symlink() or not plan.resolve().is_relative_to((path.parent / "plans").resolve()):
            raise ValueError("Plan escapes the private plans directory")
        runner = experiment if operation == "experiment" else assess
        runner(store, ROOT, read_json(plan), trust_code=True)
    elif operation != "refresh":
        raise ValueError("Unknown private operation")
    result = export_context(store)
    print(json.dumps({"operation": operation, **result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
