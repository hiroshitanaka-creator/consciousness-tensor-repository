from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from kernel.context_store import digest, make_record, text
from kernel.wound_lifecycle import SYSTEM


def git(repo, *arguments):
    completed = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *arguments],
                               capture_output=True, text=True, encoding="utf-8")
    if completed.returncode:
        raise ValueError("Git operation failed: " + completed.stderr.strip()[:500])
    return completed.stdout.strip()


def commit_for(repo, ref):
    if not isinstance(ref, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,150}", ref):
        raise ValueError("Use a named Git ref or commit hash")
    return git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")


def child_env(context_path):
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "COMSPEC", "PATHEXT",
               "LANG", "LC_ALL", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"}
    environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    environment.update(PYTHONHASHSEED="0", PYTHONIOENCODING="utf-8",
                       PYTHONDONTWRITEBYTECODE="1", CTR_EXPERIMENT_CONTEXT=str(context_path))
    return environment


def edit_fixture(root, edits):
    if not isinstance(edits, dict) or len(edits) > 12:
        raise ValueError("Fixture edits must contain at most 12 files")
    for name, content in edits.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Fixture filenames must be nonempty strings")
        path = Path(name)
        if (path.is_absolute() or ".." in path.parts or path.parts[0] in {".git", ".github", "tests"}
                or path.suffix not in {".json", ".jsonl", ".md", ".yaml", ".yml", ".txt"}):
            raise ValueError("Fixture edits are limited to data files outside tests and Git configuration")
        target = root / path
        if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
            raise ValueError("Fixture target escapes the trial checkout")
        if not isinstance(content, str) or len(content) > 64000:
            raise ValueError("Fixture content must be bounded text")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def trial(repo, commit, snapshot, *, suite="tests", timeout=30, edits=None, mode="tests"):
    if not isinstance(suite, str) or not re.fullmatch(r"[A-Za-z0-9_/-]+", suite) or ".." in suite:
        raise ValueError("Invalid test suite path")
    with tempfile.TemporaryDirectory(prefix="ctr-trial-") as directory:
        parent = Path(directory).resolve()
        worktree = parent / "checkout"
        context = parent / "context.json"
        context.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
        git(repo, "worktree", "add", "--detach", str(worktree), commit)
        try:
            edit_fixture(worktree, edits or {})
            test_dir = worktree / suite
            if test_dir.is_symlink() or not test_dir.resolve().is_relative_to(worktree.resolve()):
                raise ValueError("Test suite escapes the trial checkout")
            test_files = sorted(test_dir.rglob("test*.py")) if test_dir.exists() else []
            if not test_files and mode == "tests":
                raise ValueError("Experiment suite must contain tests")
            test_hashes = {}
            for path in sorted(test_dir.rglob("*.py")):
                if path.is_symlink() or not path.resolve().is_relative_to(worktree.resolve()):
                    raise ValueError("Symlinked test code is not allowed")
                test_hashes[path.relative_to(worktree).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            command = ([sys.executable, "-m", "unittest", "discover", "-s", suite]
                       if mode == "tests" else [sys.executable, "kernel/tensor_gate.py", "--all"])
            started = time.monotonic()
            timed_out = False
            log = parent / "output.log"
            with log.open("wb") as output:
                try:
                    process = subprocess.run(command, cwd=worktree, env=child_env(context),
                                             stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
                    returncode = process.returncode
                except subprocess.TimeoutExpired:
                    returncode, timed_out = -1, True
            content = log.read_bytes()
            match = re.search(rb"Ran (\d+) tests?", content)
            count = int(match.group(1)) if match else 0
            result = {"commit": commit, "passed": returncode == 0 and (count > 0 or mode == "axes"),
                      "returncode": returncode, "timed_out": timed_out, "tests_run": count,
                      "duration_seconds": round(time.monotonic() - started, 3),
                      "suite_hash": digest(test_hashes), "context_hash": digest(snapshot),
                      "context_bytes": len(json.dumps(snapshot, sort_keys=True).encode()),
                      "output_hash": "sha256:" + hashlib.sha256(content).hexdigest()}
            if mode == "axes":
                report = worktree / ".ctr/tensor_report.json"
                if returncode != 0 or not report.exists():
                    raise ValueError("Axis evaluation failed before producing reports")
                result["axis_vetoes"] = {axis: entry["veto"] for axis, entry in json.loads(report.read_text())["reports"].items()}
            return result
        finally:
            # Only remove the worktree created under this fresh temporary parent.
            if not worktree.resolve().is_relative_to(parent):
                raise ValueError("Unexpected trial worktree path")
            git(repo, "worktree", "remove", "--force", str(worktree))


def validate_manifest(manifest, kind):
    if not isinstance(manifest, dict) or manifest.get("kind") != kind:
        raise ValueError("Experiment kind mismatch")
    text(manifest.get("title"), "title", 300)
    text(manifest.get("acceptance"), "acceptance")
    variants = manifest.get("variants")
    if not isinstance(variants, list) or not 2 <= len(variants) <= 4:
        raise ValueError("Declare 2..4 variants, with baseline first")
    timeout = manifest.get("timeout_seconds", 30)
    if type(timeout) is not int or not 1 <= timeout <= 120 or timeout * len(variants) > 300:
        raise ValueError("Experiment budget exceeds 300 seconds")
    names = [v.get("name") for v in variants if isinstance(v, dict)]
    if len(names) != len(variants) or len(set(names)) != len(names) or names[0] != "baseline":
        raise ValueError("Variant names must be distinct and start with baseline")
    for name in names:
        text(name, "variant name", 100)
    required = manifest.get("required_pass", names)
    if not isinstance(required, list) or not required or not set(required).issubset(names):
        raise ValueError("required_pass must name declared variants")
    if kind == "forgetting" and set(required) != set(names):
        raise ValueError("Forgetting requires every variant, including baseline, to pass")
    if not isinstance(manifest.get("context_ids", []), list) or len(manifest.get("context_ids", [])) > 50:
        raise ValueError("Select at most 50 context record IDs")
    return variants, timeout


def experiment(store, repo, manifest, *, trust_code=False):
    if not trust_code:
        raise ValueError("Experiments execute repository tests; pass --trust-code after reviewing the selected refs")
    kind = manifest.get("kind") if isinstance(manifest, dict) else None
    if kind not in {"counterfactual", "forgetting"}:
        raise ValueError("Unknown experiment kind")
    variants, timeout = validate_manifest(manifest, kind)
    state = store.load()
    records = state["records"]
    context_ids = manifest.get("context_ids", [])
    if any(x not in records or records[x]["kind"] not in {"memory", "rule"} for x in context_ids):
        raise ValueError("Experiment context must select existing memory or rule IDs")
    wounds = manifest.get("wounds", [])
    if not isinstance(wounds, list) or not wounds or any(x not in records or records[x]["kind"] != "wound" for x in wounds):
        raise ValueError("An experiment must address existing wound IDs")
    selected = {key: records[key] for key in context_ids}
    hypothesis = manifest.get("hypothesis")
    if hypothesis is not None:
        proposal = records.get(hypothesis)
        if not proposal or proposal["kind"] != "hypothesis" or proposal["data"]["wound"] not in wounds:
            raise ValueError("Experiment hypothesis must address one of the declared wounds")
    refs = [commit_for(repo, variant.get("ref")) for variant in variants]
    if kind == "forgetting" and len(set(refs)) != 1:
        raise ValueError("Forgetting trials must use the same code commit")
    for index, variant in enumerate(variants):
        omitted = variant.get("omit", [])
        if not isinstance(omitted, list) or len(set(omitted)) != len(omitted):
            raise ValueError("omit must be distinct record IDs")
        if omitted and (kind != "forgetting" or index == 0):
            raise ValueError("Only non-baseline forgetting variants may omit context")
        if any(key not in selected or selected[key]["kind"] != "memory" for key in omitted):
            raise ValueError("Only selected memories may be omitted; rules and audit history are protected")
        if kind == "forgetting" and index > 0 and not omitted:
            raise ValueError("A forgetting variant must omit at least one memory")
        if kind == "forgetting" and variant.get("edits"):
            raise ValueError("Forgetting changes context only, never code or fixture data")
    identity = digest({"manifest": manifest, "commits": refs, "context": selected})
    identifier = "experiment:" + identity.split(":")[1]
    if identifier in records:
        return identifier
    results = []
    for variant, commit in zip(variants, refs):
        snapshot = {key: value for key, value in selected.items() if key not in variant.get("omit", [])}
        result = trial(repo, commit, snapshot, suite=manifest.get("suite", "tests"), timeout=timeout,
                       edits=variant.get("edits", {}))
        result.update(name=variant["name"], omitted=variant.get("omit", []))
        results.append(result)
    if len({item["suite_hash"] for item in results}) != 1:
        raise ValueError("Variants changed the test suite; compare under identical test conditions")
    required = manifest.get("required_pass", [v["name"] for v in variants])
    success = all(item["passed"] for item in results if item["name"] in required)
    if kind == "forgetting":
        success = success and all(item["context_bytes"] < results[0]["context_bytes"] for item in results[1:])
    record = make_record(identifier, "experiment", manifest["title"], manifest["acceptance"],
        ["git:" + commit for commit in refs], SYSTEM, layer="evidence", status="active",
        tags=[kind], read_when=["verify a design choice", "check failure evidence"],
        relations=[{"type": "addresses", "target": wound} for wound in wounds]
                  + ([{"type": "derived_from", "target": hypothesis}] if hypothesis else []),
        data={"kind": kind, "success": success, "wounds": wounds, "manifest": manifest,
              "variants": results, "required_pass": required, "hypothesis": hypothesis,
              "safe_omission_sets": [r["omitted"] for r in results[1:] if kind == "forgetting" and r["passed"] and results[0]["passed"]],
              "failed_omission_sets": [r["omitted"] for r in results[1:] if kind == "forgetting" and not r["passed"]],
              "acceptance_rule": "required variants pass; forgetting also reduces context bytes"})
    def operation(current):
        if identifier not in current:
            current[identifier] = record
        return identifier
    return store.transact("experiment_completed", SYSTEM, operation)
