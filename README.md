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
- `.github/workflows/issue_ingest.yml` records opened, edited, and reopened Issues in a proposed PR.

Scheduled workflows are conservative by default. They generate reports and artifacts. PR creation or compost moves require explicit workflow inputs.

## Issue ingestion

Opening, editing, or reopening an Issue triggers ingestion after the workflow has
been merged into the default branch. The workflow writes an ExperienceEvent to
`wounds/unresolved/event-issue-<number>-<revision hash>.json`, appends an audit
entry, runs tests and all five axes, then proposes the record in a PR. It never
merges the record or implements the Issue automatically. Manual runs accept an
`issue_number` and fetch a current snapshot through the GitHub API.

Enable **Allow GitHub Actions to create and approve pull requests** in repository
Settings > Actions > General for automatic PR creation. No model API key is
needed. The workflow uses `GITHUB_TOKEN` and `peter-evans/create-pull-request@v8`.
Bot-created PR workflows may need a maintainer to approve their run. See
[GitHub's workflow trigger documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
Require the Tensor Gate check through branch protection before treating it as
an enforced merge restriction; this workflow does not configure repository rules.

Each record contains source text, the repository and Issue number, timestamps,
source and contradiction-context hashes, and provisional wound candidates.
The trace timestamp records the source revision's update time.
English and Japanese keyword rules connect it to existing contradictions;
all records also reference `observation-vs-task`. Unmatched requests remain
unassimilated for review. Keyword matches are not diagnoses or inferred motives.

Replaying an identical source revision does not add another file or trace.
Edits and reopenings get separate revisions, so out-of-order deliveries cannot
overwrite newer observations. Manual snapshots are a separate observation action.
A retry repairs a missing trace if file creation succeeded before interruption.
Run only one local writer per checkout. Actions give revisions separate branches
and serialize matching deliveries. Independent PRs may conflict in the shared
ledger when merged; review those conflicts without discarding either trace.

The 90-day TTL is a review date, not an automatic deletion command. Per-event
compost transitions are not yet connected to the existing compost scanner.
Raw title and body are retained; editing an Issue does not remove merged history.
The workflow also uploads a 30-day artifact, including when PR publication fails.

Local replay of a GitHub `issues` webhook payload:

```powershell
python kernel/experience_event.py --event-file issue-event.json
```

Use `--root <directory>` for an isolated output checkout containing
`contradiction_matrix.json`. The CLI also accepts
`--issue-file issue.json --repository owner/repo` for GitHub REST Issue JSON. Console output contains
record paths and status, not the Issue body.

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
