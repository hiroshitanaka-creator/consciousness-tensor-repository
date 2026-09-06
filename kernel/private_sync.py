from __future__ import annotations

import json
import subprocess

from kernel.context_store import ContextStore


def resume_state(store, pending):
    ContextStore.validate_state(pending)
    with store.lock():
        current = store.load()
        if (current["owner"], current["synthetic"]) != (pending["owner"], pending["synthetic"]):
            raise ValueError("Pending context belongs to another store")
        if pending["audit"][:len(current["audit"])] == current["audit"]:
            store.save(pending)
            return True
        if current["audit"][:len(pending["audit"])] == pending["audit"]:
            return False
        raise ValueError("Pending and main context histories diverged; reconcile their source records before continuing")


def restore_pending(store, repository, branch):
    response = subprocess.run(["gh", "pr", "list", "--repo", repository, "--head", branch,
                               "--state", "open", "--json", "headRefOid"],
                              capture_output=True, text=True, check=True)
    pulls = json.loads(response.stdout)
    if not pulls:
        return False
    commit = pulls[0]["headRefOid"]
    subprocess.run(["git", "fetch", "--quiet", "origin", commit], check=True)
    result = subprocess.run(["git", "show", commit + ":context/state.json"],
                            capture_output=True, text=True, encoding="utf-8", check=True)
    return resume_state(store, json.loads(result.stdout))
