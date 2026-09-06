from __future__ import annotations

from kernel.context_store import AXES, digest, make_record, now, text
from kernel.experience_event import build_experience_event

SYSTEM = {"type": "system", "id": "ctr-lifecycle"}
TRANSITIONS = {"unresolved": {"investigating"}, "investigating": {"scarred", "unresolved"},
               "recurring": {"investigating"}, "scarred": set()}


def ingest_experience(store, payload):
    event = build_experience_event(payload)
    revision = event["revision_id"].split(":")[1]
    identifier = "experience:" + revision
    source = event["source"]["url"] + "@" + event["revision_id"]

    def operation(records):
        if identifier in records:
            return {"id": identifier, "duplicate": True}
        actor = {"type": "system", "id": "github-issue-ingestion"}
        records[identifier] = make_record(identifier, "experience", event["surface_request"][:400],
            event["source"]["body"] or event["surface_request"], [source], actor,
            status="active", tags=event["possible_wounds"], data={"event": event},
            relations=[{"type": "addresses", "target": "wound:" + wound} for wound in event["possible_wounds"]])
        for wound in event["possible_wounds"]:
            wound_id = "wound:" + wound
            if wound_id not in records:
                records[wound_id] = make_record(wound_id, "wound", wound,
                    "Provisional contradiction connected to source observations. Review before deciding.",
                    [source], actor, status="unresolved", tags=[wound],
                    data={"occurrences": [], "recurrences": 0, "history": []})
            record = records[wound_id]
            data = record["data"]
            if identifier not in data["occurrences"]:
                data["occurrences"].append(identifier)
                record["relations"].append({"type": "derived_from", "target": identifier})
                if record["status"] == "scarred" and event["source"]["updated_at"] > data.get("scarred_source_time", ""):
                    record["status"] = "recurring"
                    data["recurrences"] += 1
                    data["history"].append({"to": "recurring", "source": identifier, "timestamp": now()})
                record["updated_at"] = now()
        return {"id": identifier, "duplicate": False, "wounds": event["possible_wounds"]}
    return store.transact("experience_observed", SYSTEM, operation)


def record_decision(store, proposal, accept=False):
    if not isinstance(proposal, dict):
        raise ValueError("Decision must be an object")
    for field in ("id", "title", "choice", "cost", "failure_condition"):
        text(proposal.get(field), field)
    alternatives = proposal.get("alternatives")
    if not isinstance(alternatives, list) or len(alternatives) < 2 or not all(isinstance(x, str) and x.strip() for x in alternatives):
        raise ValueError("Name at least two rejected alternatives")
    evidence = proposal.get("evidence", [])
    if not isinstance(evidence, list) or not all(isinstance(x, str) for x in evidence):
        raise ValueError("Evidence must be record IDs")
    axes = proposal.get("axes", {})
    if accept and (set(axes) != set(AXES) or any(v is not False for v in axes.values())):
        raise ValueError("Every axis must explicitly have veto=false to accept a decision")
    record = make_record(proposal["id"], "decision", proposal["title"], proposal["choice"],
        proposal.get("sources", []), proposal.get("actor"), layer="decisions",
        status="accepted" if accept else "proposed", tags=proposal.get("tags", []),
        relations=[{"type": "depends_on", "target": item} for item in evidence],
        data={key: proposal.get(key) for key in ("choice", "alternatives", "cost", "failure_condition", "evidence", "axes")})
    if not record["id"].startswith("decision:"):
        raise ValueError("Decision IDs must start with decision:")

    def operation(records):
        for identifier in evidence:
            if identifier not in records or records[identifier]["kind"] not in {"experiment", "evaluation"}:
                raise ValueError("Decision evidence must refer to existing experiment or evaluation records")
        if accept and not evidence:
            raise ValueError("Accepting a decision requires experiment or evaluation evidence")
        existing = records.get(record["id"])
        if existing:
            comparable = {k: v for k, v in record.items() if k != "updated_at"}
            prior = {k: v for k, v in existing.items() if k != "updated_at"}
            if prior != comparable:
                raise ValueError("Use a new decision ID for a changed choice")
            return existing["id"]
        records[record["id"]] = record
        return record["id"]
    return store.transact("decision_accepted" if accept else "decision_proposed", record["actor"], operation)


def transition(store, wound_id, target, *, decision=None, evidence=None):
    def operation(records):
        wound = records.get(wound_id)
        if not wound or wound["kind"] != "wound":
            raise ValueError("Unknown wound")
        if target == wound["status"]:
            return wound_id
        if target not in TRANSITIONS.get(wound["status"], set()):
            raise ValueError("Invalid wound transition")
        if target == "scarred":
            choice, proof = records.get(decision), records.get(evidence)
            if not choice or choice["kind"] != "decision" or choice["status"] != "accepted":
                raise ValueError("Scarring requires an accepted decision")
            if not proof or proof["kind"] != "experiment" or not proof["data"].get("success"):
                raise ValueError("Scarring requires a successful experiment")
            if evidence not in choice["data"]["evidence"] or wound_id not in proof["data"].get("wounds", []):
                raise ValueError("Decision and experiment must address this wound")
            wound["relations"].extend([{"type": "depends_on", "target": decision}, {"type": "depends_on", "target": evidence}])
            wound["data"]["scarred_source_time"] = max(
                records[x]["data"]["event"]["source"]["updated_at"] for x in wound["data"]["occurrences"])
        wound["data"]["history"].append({"from": wound["status"], "to": target,
                                         "decision": decision, "evidence": evidence, "timestamp": now()})
        wound["status"] = target
        wound["updated_at"] = now()
        return wound_id
    return store.transact("wound_transition", SYSTEM, operation)


def compost_record(store, identifier, decision_id):
    def operation(records):
        record, choice = records.get(identifier), records.get(decision_id)
        if not record or record["kind"] not in {"memory", "hypothesis"}:
            raise ValueError("Only memories and hypotheses can retire through this command")
        if not choice or choice["kind"] != "decision" or choice["status"] != "accepted":
            raise ValueError("Retirement requires an accepted decision")
        if record["status"] != "composted":
            record["status"] = "composted"
            record["relations"].append({"type": "depends_on", "target": decision_id})
        return identifier
    return store.transact("record_composted", SYSTEM, operation)
