import json
import shutil
import subprocess
from pathlib import Path

from kernel.context_store import make_record
from kernel.repository import ROOT

ACTOR = {"type": "assistant", "id": "test-agent"}
WOUND = "wound:minimality-vs-ecology"


def payload(action="opened", timestamp="2026-09-01T12:00:00Z", number=52):
    return {"action": action, "repository": {"full_name": "example/context"},
            "issue": {"number": number, "title": "Memory retention", "body": "Record memory without indefinite retention.",
                      "created_at": "2026-09-01T12:00:00Z", "updated_at": timestamp, "state": "open"}}


def memory(identifier="memory:essential", body="Retention must not exceed 90 days."):
    return make_record(identifier, "memory", identifier, body, ["fixture:retention"], ACTOR,
                       tags=["retention", "memory"], read_when=["choose memory retention"])


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def trial_repo(root):
    repo = root / "trial-repository"
    shutil.copytree(ROOT / "examples/evolution/trial_project", repo)
    git(repo, "init")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=CTR Tests", "-c", "user.email=ctr-tests@example.invalid", "commit", "-m", "Synthetic trial")
    return repo


def decision(evidence, identifier="decision:retention"):
    return {"id": identifier, "title": "Keep bounded retention", "choice": "Retain only necessary records.",
            "cost": "Long-term context can be lost.", "failure_condition": "A required task loses essential context.",
            "alternatives": ["Keep everything indefinitely.", "Discard all context immediately."],
            "evidence": [evidence], "sources": ["fixture:retention"], "actor": ACTOR,
            "axes": {axis: False for axis in ("null", "existential", "fudo", "shadow", "transparency")}}


def manifest(kind="counterfactual"):
    return {"kind": kind, "title": "Retention experiment", "acceptance": "The required variants retain the bounded-memory contract.",
            "wounds": [WOUND], "context_ids": ["memory:essential", "memory:redundant"], "timeout_seconds": 15,
            "variants": [{"name": "baseline", "ref": "HEAD"},
                         {"name": "candidate", "ref": "HEAD", **({"omit": ["memory:redundant"]} if kind == "forgetting"
                           else {"edits": {"policy.json": json.dumps({"retention_days": 365})}})}],
            "required_pass": ["baseline", "candidate"] if kind == "forgetting" else ["baseline"]}
