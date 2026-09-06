from __future__ import annotations

import random
import re
import os

from kernel.context_store import digest, make_record, text
from kernel.wound_lifecycle import SYSTEM

QUESTIONS = (
    ("Could a smaller retained context support the same decisions?",
     "Compare a baseline context with one memory withheld; keep the same test suite.",
     "No previously passing task may fail after omission.", "forgetting"),
    ("Was a rejected alternative excluded because it challenged the preferred design?",
     "Run the accepted and rejected Git refs against the same declared checks.",
     "The alternative must pass the declared checks within the same time limit.", "counterfactual"),
    ("Does the gate mistake preferred vocabulary for evidence?",
     "Run labeled positive and negative fixtures through all five current agents.",
     "Measure false acceptances and false rejections separately for each axis.", "assessment"),
)


def dream(store, wound_id, seed=0):
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("seed must be a 32-bit unsigned integer")

    def operation(records):
        wound = records.get(wound_id)
        if not wound or wound["kind"] != "wound":
            raise ValueError("Dreams require an existing wound")
        sources = sorted(set([wound_id, *wound["data"]["occurrences"]]))
        source_hash = digest({key: records[key] for key in sources})
        key = digest({"wound": wound_id, "sources": source_hash, "seed": seed})
        identifier = "hypothesis:" + key.split(":")[1]
        if identifier in records:
            return identifier
        index = random.Random(str(seed) + source_hash).randrange(len(QUESTIONS))
        question, experiment, criterion, experiment_kind = QUESTIONS[index]
        related = [r["id"] for r in records.values() if r["kind"] in {"decision", "hypothesis"} and r["status"] in {"rejected", "composted"}]
        records[identifier] = make_record(identifier, "hypothesis", wound["title"] + ": " + experiment_kind,
            question, [wound_id, source_hash], SYSTEM, layer="residues", status="proposed",
            tags=[wound["title"], experiment_kind], read_when=["reconsider this unresolved contradiction"],
            relations=[{"type": "derived_from", "target": key} for key in sources + related[:5]],
            data={"seed": seed, "generator": "ctr-template-v1", "source_hash": source_hash,
                  "question": question, "experiment": experiment, "acceptance_criterion": criterion,
                  "experiment_kind": experiment_kind, "wound": wound_id,
                  "branch": os.environ.get("CTR_PENDING_BRANCH", "dream/" + identifier.split(":")[1][:16]),
                  "branch_status": "workflow-target" if os.environ.get("CTR_PENDING_BRANCH") else "suggested",
                  "main_merge_allowed": False, "required_audits": ["null", "existential", "transparency"],
                  "interpretation": "A template-generated project hypothesis, not an inference about a person."})
        return identifier
    return store.transact("hypothesis_generated", SYSTEM, operation)


def review_dream(store, hypothesis_id, disposition, decision_id):
    if disposition not in {"accepted", "rejected"}:
        raise ValueError("Choose accepted or rejected")

    def operation(records):
        hypothesis, choice = records.get(hypothesis_id), records.get(decision_id)
        if not hypothesis or hypothesis["kind"] != "hypothesis":
            raise ValueError("Unknown hypothesis")
        if not choice or choice["kind"] != "decision" or choice["status"] != "accepted":
            raise ValueError("Dream review requires an accepted, evidence-backed decision")
        if hypothesis["status"] == disposition:
            return hypothesis_id
        if hypothesis["status"] != "proposed":
            raise ValueError("This hypothesis has already been reviewed")
        if disposition == "accepted":
            proofs = [records[x] for x in choice["data"]["evidence"]]
            if not any(p["kind"] in {"experiment", "evaluation"} and p["data"].get("success")
                       and p["data"].get("hypothesis") == hypothesis_id
                       and p["data"].get("kind") == hypothesis["data"].get("experiment_kind")
                       and hypothesis["data"]["wound"] in p["data"].get("wounds", []) for p in proofs):
                raise ValueError("Assimilation requires a successful experiment for the same wound")
        hypothesis["status"] = disposition
        hypothesis["relations"].append({"type": "depends_on", "target": decision_id})
        return hypothesis_id
    return store.transact("hypothesis_reviewed", SYSTEM, operation)


def propose_dream(store, proposal):
    if not isinstance(proposal, dict):
        raise ValueError("Hypothesis proposal must be an object")
    for key in ("title", "question", "experiment", "acceptance_criterion", "wound"):
        text(proposal.get(key), key)
    generation = proposal.get("generation", {})
    for key in ("model", "prompt_hash", "provider"):
        text(generation.get(key), "generation." + key, 300)
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", generation["prompt_hash"]):
        raise ValueError("Declare a SHA-256 prompt hash")
    sources = proposal.get("source_ids")
    if not isinstance(sources, list) or not sources:
        raise ValueError("External hypotheses must identify source record IDs")
    if proposal.get("experiment_kind") not in {"counterfactual", "forgetting", "assessment"}:
        raise ValueError("Choose a supported experiment_kind")
    identifier = "hypothesis:" + digest(proposal).split(":")[1]
    def operation(records):
        wound = records.get(proposal["wound"])
        if not wound or wound["kind"] != "wound" or any(key not in records for key in sources):
            raise ValueError("Hypothesis sources and wound must already exist")
        if identifier not in records:
            records[identifier] = make_record(identifier, "hypothesis", proposal["title"], proposal["question"],
                sources, proposal.get("actor"), layer="residues", status="proposed",
                relations=[{"type": "derived_from", "target": key} for key in sources],
                data={"wound": proposal["wound"], "question": proposal["question"],
                      "experiment": proposal["experiment"], "acceptance_criterion": proposal["acceptance_criterion"],
                      "experiment_kind": proposal["experiment_kind"],
                      "generator": "external-proposal", "generation": generation,
                      "source_hashes": {key: digest(records[key]) for key in sources},
                      "output_hash": digest(proposal), "main_merge_allowed": False,
                      "branch": os.environ.get("CTR_PENDING_BRANCH", "dream/" + identifier.split(":")[1][:16]),
                      "branch_status": "workflow-target" if os.environ.get("CTR_PENDING_BRANCH") else "suggested",
                      "required_audits": ["null", "existential", "transparency"],
                      "interpretation": "External model metadata is declared provenance, not independently authenticated."})
        return identifier
    return store.transact("external_hypothesis_proposed", proposal.get("actor"), operation)
