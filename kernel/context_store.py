from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kernel.repository import ROOT

KINDS = {"experience", "wound", "hypothesis", "decision", "experiment", "evaluation", "memory", "rule"}
EDGES = {"addresses", "supports", "contradicts", "supersedes", "depends_on", "derived_from"}
LAYERS = {"rules", "current", "decisions", "evidence", "relations", "residues"}
STATUSES = {"active", "proposed", "accepted", "rejected", "unresolved", "investigating", "scarred", "recurring", "composted", "superseded"}
AXES = ("null", "existential", "fudo", "shadow", "transparency")


def digest(value):
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError("Input exceeds 2 MB")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def text(value, name, limit=64000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be nonempty text of at most {limit} characters")
    return value


def validate_record(record):
    if not isinstance(record, dict):
        raise ValueError("Record must be an object")
    if not re.fullmatch(r"[a-z][a-z0-9_-]*:[A-Za-z0-9_.:-]+", str(record.get("id", ""))):
        raise ValueError("Record ID must be a namespaced identifier")
    if record.get("kind") not in KINDS or record.get("layer") not in LAYERS or record.get("status") not in STATUSES:
        raise ValueError("Unknown record kind, layer, or status")
    text(record.get("title"), "title", 400)
    text(record.get("body"), "body")
    for key in ("updated_at", "review_after"):
        value = text(record.get(key), key, 50)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"{key} must be an ISO timestamp") from None
        if parsed.tzinfo is None:
            raise ValueError(f"{key} must include a timezone")
    for key in ("sources", "read_when", "tags"):
        values = record.get(key)
        if not isinstance(values, list) or len(values) > 50 or not all(isinstance(v, str) and v.strip() for v in values):
            raise ValueError(f"{key} must be a bounded list of nonempty strings")
    if not record["sources"]:
        raise ValueError("A source is required")
    actor = record.get("actor", {})
    if not isinstance(actor, dict) or actor.get("type") not in {"human", "assistant", "system"}:
        raise ValueError("Declare actor.type; never infer human approval")
    text(actor.get("id"), "actor.id", 200)
    if type(record.get("ttl_days")) is not int or not 1 <= record["ttl_days"] <= 3650:
        raise ValueError("ttl_days must be 1..3650")
    relations = record.get("relations", [])
    if not isinstance(relations, list) or len(relations) > 100:
        raise ValueError("Too many relations")
    for edge in relations:
        if not isinstance(edge, dict) or edge.get("type") not in EDGES:
            raise ValueError("Unknown graph relationship")
        text(edge.get("target"), "relation.target", 250)
    if not isinstance(record.get("data", {}), dict):
        raise ValueError("data must be an object")


def make_record(identifier, kind, title, body, sources, actor, *, layer="current",
                status="active", tags=(), read_when=(), relations=(), ttl_days=90, data=None):
    record = dict(id=identifier, kind=kind, title=title, body=body, sources=list(sources),
                  actor=actor, layer=layer, status=status, tags=list(tags), read_when=list(read_when),
                  relations=list(relations), ttl_days=ttl_days, data=data or {}, updated_at=now(),
                  review_after=(datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat(timespec="seconds"))
    validate_record(record)
    return record


def filename(identifier):
    return hashlib.sha256(identifier.encode()).hexdigest() + ".json"


class ContextStore:
    """One atomic canonical state; indexes and browse files are disposable projections."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        engine = ROOT.resolve()
        if self.root.is_relative_to(engine) and not self.root.is_relative_to(engine / ".ctr"):
            raise ValueError("Personal context must be outside the public engine checkout")
        self.path = self.root / "state.json"

    def init(self, owner, synthetic=False):
        text(owner, "owner", 200)
        self.root.mkdir(parents=True, exist_ok=True)
        if os.environ.get("GITHUB_REPOSITORY_VISIBILITY") == "public" and not synthetic:
            raise ValueError("Personal context cannot run in a public Actions repository")
        with self.lock():
            if self.path.exists():
                return self.load()
            state = {"version": 1, "owner": owner, "synthetic": synthetic, "records": {}, "audit": []}
            self.save(state)
            return state

    @contextmanager
    def lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / ".writer-lock"
        try:
            lock.mkdir()
        except FileExistsError:
            raise ValueError("Context is locked by another writer; inspect interrupted runs before recovery") from None
        try:
            yield
        finally:
            lock.rmdir()

    def load(self):
        if not self.path.is_file() or self.path.is_symlink():
            raise ValueError("Initialize a context store first; symlinked state is not allowed")
        state = json.loads(self.path.read_text(encoding="utf-8"))
        return self.validate_state(state)

    @staticmethod
    def validate_state(state):
        if state.get("version") != 1 or not isinstance(state.get("records"), dict):
            raise ValueError("Unsupported context state")
        previous = "genesis"
        for event in state["audit"]:
            payload = {k: v for k, v in event.items() if k != "hash"}
            if event["previous"] != previous or event["hash"] != digest(payload):
                raise ValueError("Context audit chain is inconsistent")
            previous = event["hash"]
        for identifier, record in state["records"].items():
            validate_record(record)
            if identifier != record["id"]:
                raise ValueError("Record ID mismatch")
        changes = [e for e in state["audit"] if "after" in e["details"]]
        if state["records"] and not changes:
            raise ValueError("Context records have no mutation audit")
        if changes and changes[-1]["details"]["after"] != digest(state["records"]):
            raise ValueError("Context state does not match its audit digest")
        return state

    def save(self, state):
        if self.path.is_symlink():
            raise ValueError("Symlinked state is not allowed")
        content = json.dumps(state, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        fd, temporary = tempfile.mkstemp(prefix=".state-", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def transact(self, action, actor, operation):
        with self.lock():
            state = self.load()
            before = digest(state["records"])
            result = operation(state["records"])
            for record in state["records"].values():
                validate_record(record)
            after = digest(state["records"])
            if after != before:
                self.audit(state, action, actor, {"before": before, "after": after})
                self.save(state)
            return result

    @staticmethod
    def audit(state, action, actor, details):
        event = {"action": action, "actor": actor, "timestamp": now(), "details": details,
                 "previous": state["audit"][-1]["hash"] if state["audit"] else "genesis"}
        event["hash"] = digest(event)
        state["audit"].append(event)

    def note(self, action, actor, details):
        with self.lock():
            state = self.load()
            self.audit(state, action, actor, details)
            self.save(state)

    def add(self, record):
        validate_record(record)
        if record["kind"] not in {"memory", "rule"} or record["status"] not in {"active", "proposed"}:
            raise ValueError("Use domain commands for wounds, decisions, hypotheses, and evidence")

        def operation(records):
            existing = records.get(record["id"])
            if existing and existing != record:
                raise ValueError("Existing record is immutable; add a new ID and supersede it")
            for edge in record["relations"]:
                if edge["target"] not in records:
                    raise ValueError("Relation target does not exist")
            records[record["id"]] = record
            return record["id"]
        return self.transact("record_added", record["actor"], operation)
