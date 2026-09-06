from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.contradiction_engine import extract_active_contradictions
from kernel.ledger import append_trace_event, sha256_text
from kernel.repository import ROOT, parse_jsonl, write_json


ACTIONS = ("opened", "edited", "reopened", "snapshot")
CLASSIFIER = "ctr-keywords-v1"
# These are review candidates, not conclusions about the author's motives.
WOUND_TERMS = {
    "minimality-vs-ecology": ("memory", "history", "delete", "\u8a18\u61b6", "\u5c65\u6b74", "\u524a\u9664"),
    "transparency-vs-shadow": ("dream", "shadow", "audit", "\u5922", "\u5f71", "\u76e3\u67fb"),
    "comfort-vs-decision": ("automatic", "convenience", "decision", "\u81ea\u52d5", "\u4fbf\u5229", "\u6c7a\u65ad"),
}


def _text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be a nonempty string of at most {limit} characters")
    return value


def _timestamp(value: Any, field: str) -> datetime:
    text = _text(value, field, 40)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field} must be an ISO 8601 timestamp") from None
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def build_experience_event(payload: Any, root: Path = ROOT) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Issue payload must be an object")
    action = payload.get("action")
    if action not in ACTIONS:
        raise ValueError("Unsupported Issue action")
    issue = payload.get("issue")
    repository = payload.get("repository")
    if not isinstance(issue, dict) or not isinstance(repository, dict):
        raise ValueError("Issue payload needs issue and repository objects")
    if "pull_request" in issue:
        raise ValueError("Pull requests cannot be ingested as Issues")
    repo = repository.get("full_name")
    if not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("repository.full_name must identify an owner/repository")
    number = issue.get("number")
    if type(number) is not int or number < 1:
        raise ValueError("issue.number must be a positive integer")
    title = _text(issue.get("title"), "issue.title", 1024)
    body = issue.get("body")
    if body is None:
        body = ""
    if not isinstance(body, str) or len(body) > 262144:
        raise ValueError("issue.body must be a string of at most 262144 characters or null")
    created = _timestamp(issue.get("created_at"), "issue.created_at")
    updated = _timestamp(issue.get("updated_at"), "issue.updated_at")
    if updated < created:
        raise ValueError("issue.updated_at cannot precede issue.created_at")
    try:
        review_after = (updated + timedelta(days=90)).isoformat()
    except OverflowError:
        raise ValueError("issue.updated_at leaves no room for the decay review date") from None
    state = issue.get("state")
    if state not in ("open", "closed"):
        raise ValueError("issue.state must be open or closed")

    source = {
        "repository": repo,
        "number": number,
        "url": f"https://github.com/{repo}/issues/{number}",
        "title": title,
        "body": body,
        "created_at": created.isoformat(),
        "updated_at": updated.isoformat(),
        "state": state,
        "action": action,
    }
    source_hash = sha256_text(json.dumps(source, sort_keys=True))
    revision = source_hash.removeprefix("sha256:")
    active = extract_active_contradictions(root)
    if "observation-vs-task" not in active:
        raise ValueError("contradiction_matrix.json must preserve observation-vs-task")
    content = (title + "\n" + body).casefold()
    matches = {
        wound: [term for term in terms if term in content]
        for wound, terms in WOUND_TERMS.items() if wound in active
    }
    matches = {wound: terms for wound, terms in matches.items() if terms}
    return {
        "event_id": f"event:{repo}:issue-{number}",
        "revision_id": source_hash,
        "raw_issue": f"#{number} {title}",
        "surface_request": title,
        "initial_status": "unassimilated",
        "possible_wounds": ["observation-vs-task", *sorted(matches)],
        "classification": {"method": CLASSIFIER, "matched_terms": matches, "requires_review": True},
        "source": source,
        "context_hash": sha256_text((root / "contradiction_matrix.json").read_text(encoding="utf-8")),
        "decay": {
            "ttl_days": 90,
            "review_after": review_after,
            "policy": "review_before_compost",
            "compost_target": f"compost/issues/issue-{number}-{revision}.json",
        },
    }


def ingest(payload: Any, root: Path = ROOT) -> dict[str, Any]:
    event = build_experience_event(payload, root)
    number = event["source"]["number"]
    revision = event["revision_id"].removeprefix("sha256:")
    relative_path = f"wounds/unresolved/event-issue-{number}-{revision}.json"
    path = root / relative_path
    for target in (path, root / "trace_ledger.jsonl"):
        if not target.resolve().is_relative_to(root.resolve()):
            raise ValueError("Ingestion output must remain inside the repository")
    # Validate the ledger before writing. A retry also repairs an interrupted append.
    records = parse_jsonl("trace_ledger.jsonl", root)
    created = not path.exists()
    if not created:
        stored = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(stored, dict)
                or stored.get("revision_id") != event["revision_id"]
                or stored.get("source") != event["source"]):
            raise ValueError("Existing ExperienceEvent does not match its source revision")
        # A newer classifier or matrix must not rewrite an already observed revision.
        event = stored
    content = path.read_text(encoding="utf-8") if not created else json.dumps(event, indent=2, sort_keys=True) + "\n"
    output_hash = sha256_text(content)
    source_ref = f"{event['source']['url']}@{event['revision_id']}"
    prior_traces = [record for record in records if
        record.get("event") == "experience_ingested"
        and source_ref in record.get("input_sources", [])
    ]
    if any(record.get("output_hash") != output_hash for record in prior_traces):
        raise ValueError("ExperienceEvent content differs from its recorded trace hash")
    recorded = bool(prior_traces)
    if created:
        write_json(relative_path, event, root)
    if not recorded:
        append_trace_event({
            "timestamp": event["source"]["updated_at"],
            "event": "experience_ingested",
            "model": "none",
            "prompt_hash": sha256_text(event["classification"]["method"]),
            "input_sources": [source_ref, "contradiction_matrix.json@" + event["context_hash"]],
            "output_hash": output_hash,
            "bias_risks": ["keyword matching is not intent inference", "Issue wording and language bias"],
        }, root)
    return {
        "created": created,
        "trace_appended": not recorded,
        "path": relative_path,
        "branch": f"codex/experience-issue-{number}-{revision}",
        "issue_number": number,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Register an Issue snapshot as an unassimilated ExperienceEvent.")
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--event-file", type=Path, help="GitHub issues webhook JSON; defaults to GITHUB_EVENT_PATH.")
    sources.add_argument("--issue-file", type=Path, help="GitHub REST Issue JSON for a manual snapshot.")
    parser.add_argument("--repository", help="owner/repository for --issue-file")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        source = args.issue_file or args.event_file or os.environ.get("GITHUB_EVENT_PATH")
        if not source:
            raise ValueError("Supply --event-file, --issue-file, or GITHUB_EVENT_PATH")
        path = Path(source)
        if path.stat().st_size > 2_000_000:
            raise ValueError("Issue payload exceeds the 2 MB ingestion limit")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if args.issue_file:
            payload = {"action": "snapshot", "issue": payload, "repository": {"full_name": args.repository}}
        result = ingest(payload, args.root)
        if os.environ.get("GITHUB_OUTPUT"):
            with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as handle:
                for key in ("path", "branch", "issue_number"):
                    handle.write(f"{key}={result[key]}\n")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        # Invalid JSON may contain Issue text, so do not echo the raw payload.
        message = "Invalid JSON input or stored record" if isinstance(exc, json.JSONDecodeError) else str(exc)
        print(f"ExperienceEvent ingestion failed: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
