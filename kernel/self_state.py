from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.contradiction_engine import extract_active_contradictions
from kernel.ledger import repo_tree_hash, sha256_file, sha256_text
from kernel.repository import ROOT, parse_jsonl


def _hash_or_missing(path: Path) -> str:
    return sha256_file(path) if path.exists() else "missing"


def build_self_state(root: Path = ROOT) -> dict[str, object]:
    current_goal = (root / "CONSCIOUSNESS.md").read_text(encoding="utf-8")
    wounds = extract_active_contradictions(root)
    shadow_records = parse_jsonl("shadow_hypotheses.jsonl", root)
    shadow_ids = [record.get("shadow_hypothesis_id", "shadow:unknown") for record in shadow_records]
    return {
        "self_state_id": repo_tree_hash(root),
        "repo_tree_hash": repo_tree_hash(root),
        "current_goal_hash": sha256_text(current_goal),
        "memory_digest": _hash_or_missing(root / "relation_graph.yaml"),
        "active_wounds": wounds,
        "deleted_self_claims": [
            "I am helpful",
            "I optimize user satisfaction",
            "I have stable identity",
        ],
        "irreversible_decisions": [
            "decision:make-five-axis-veto-required",
            "decision:reject-chatbot-personality-interface",
            "decision:store-shadow-as-quarantined-artifact",
        ],
        "relation_graph_hash": _hash_or_missing(root / "relation_graph.yaml"),
        "shadow_seed_hash": sha256_text(",".join(shadow_ids)),
        "bias_manifest_hash": _hash_or_missing(root / "bias_manifest.yaml"),
        "trace_ledger_hash": _hash_or_missing(root / "trace_ledger.jsonl"),
    }


def render_self_md(state: dict[str, object]) -> str:
    wounds = "\n".join(f"- {item}" for item in state["active_wounds"])
    deleted = "\n".join(f"- {item}" for item in state["deleted_self_claims"])
    decisions = "\n".join(f"- {item}" for item in state["irreversible_decisions"])
    return f"""# SELF

I am not a personality.
I am the current unresolved contradiction state of this repository.

## Current irreducible claims

- Claim 1: CTR rejects phenomenal-consciousness claims and implements only audit-visible repository pressure.
- Claim 2: Every mergeable change must satisfy five independent veto axes.
- Claim 3: Contradictions must be preserved as structured evidence instead of dissolved into consensus.

## Current wounds

{wounds}

## Claims deleted since last cycle

{deleted}

## Decisions I cannot undo

{decisions}

## Relations that currently constitute me

- relation_graph_hash: {state["relation_graph_hash"]}
- trace_ledger_hash: {state["trace_ledger_hash"]}
- bias_manifest_hash: {state["bias_manifest_hash"]}

## Shadow hypotheses currently quarantined

- shadow_seed_hash: {state["shadow_seed_hash"]}

## Audit hash

- {state["self_state_id"]}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print", action="store_true", dest="print_state")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    state = build_self_state()
    rendered = render_self_md(state)
    if args.write:
        (ROOT / "SELF.md").write_text(rendered, encoding="utf-8")
    if args.check:
        current = (ROOT / "SELF.md").read_text(encoding="utf-8")
        if current != rendered:
            print("SELF.md is stale; run python kernel/self_state.py --write")
            return 1
    if args.print_state or not (args.write or args.check):
        print(json.dumps(state, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
