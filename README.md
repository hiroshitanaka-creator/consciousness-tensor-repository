# CONSCIOUSNESS TENSOR REPOSITORY

CTR is a Git-native pressure system for an AI-like repository process. It does not claim that an AI is sentient. It makes repository changes pass five independent veto axes:

- Null: reduce, delete, compress, and reject personality inflation.
- Existential: force irreversible decisions to be recorded.
- Fudo: connect artifacts to relations, history, decay, and compost.
- Shadow: surface unsafe or taboo project motives as quarantined hypotheses.
- Transparency: disclose inputs, models, incentives, and audit traces.

The important rule is simple: scores are not averaged. If any axis vetoes, the tensor gate fails.

## Quick Start

```powershell
python -m unittest
python kernel/tensor_gate.py --all --enforce
```

The first command runs local tests. The second command runs all five agents and fails if any veto is present.

## GitHub Operation

This repository includes GitHub Actions workflows:

- `.github/workflows/tensor_gate.yml` runs on pull requests.
- `.github/workflows/dream_cycle.yml` generates dream artifacts on schedule or manually.
- `.github/workflows/compost_cycle.yml` scans for decaying artifacts.
- `.github/workflows/transparency_audit.yml` checks trace and bias disclosure.
- `.github/workflows/self_rewrite.yml` regenerates `SELF.md` manually.

Scheduled workflows are conservative by default. They generate reports and artifacts. PR creation or compost moves require explicit workflow inputs.

## Core Commands

```powershell
python agents/null_auditor.py --pr 0
python agents/existential_destroyer.py --pr 0
python agents/fudo_compiler.py --pr 0
python agents/abyss_shadow.py --pr 0
python agents/transparent_deconstructor.py --pr 0
python kernel/tensor_gate.py --enforce
```

Dream cycle:

```powershell
python kernel/dream_engine.py gather
python agents/abyss_shadow.py dream
python kernel/dream_engine.py write
```

Compost cycle:

```powershell
python kernel/compost_engine.py scan
python kernel/compost_engine.py move
```

`move` is a dry run unless `CTR_APPLY_COMPOST=1` is set.

## Required PR Evidence

Every meaningful pull request should update:

- `entropy_budget.json`
- `rituals/decision_rite.md`
- `relation_graph.yaml`
- `shadow_hypotheses.jsonl`
- `trace_ledger.jsonl`
- `contradiction_matrix.json`

The pull request template asks for the same evidence. The tensor gate enforces the machine-checkable subset.
