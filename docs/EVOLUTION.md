# Evolution and context graph

CTR 0.2 adds six connected capabilities. The public repository contains the engine,
schemas, documentation, and synthetic fixtures. Put personal records in a separate
private data repository. The original root-level Issue/Dream commands remain for
the public engine's own development; they are not the personal data store.

## Capabilities and acceptance conditions

| Capability | Observable behavior |
| --- | --- |
| Wound lifecycle | Issue revisions accumulate under wound IDs; unresolved/investigating/scarred/recurring transitions preserve history. Scarring needs a successful experiment and an accepted decision linked to the same wound. |
| Counterfactual experiments | Declared Git refs and data variants run the same test suite in fresh detached worktrees. Store commits, suite/context hashes, return codes, test counts, and elapsed time. |
| Experimental Dream | Seeded source-dependent templates or external model proposals produce quarantined hypotheses with an experiment and acceptance condition. Assimilation needs a matching successful experiment or assessment plus an accepted decision. |
| Forgetting experiments | Run the same code/tests with selected memories omitted from a copied context. Report passing/failing omission sets and byte reduction. Original records, rules, and audit history remain intact. |
| Judge assessment | Run the real five agents on labeled fixtures and record false vetoes and missed vetoes per axis. Never average axes or modify thresholds automatically. |
| Context graph | Generate a layered index, per-record files, typed relations, and a self-state. Search English/Japanese terms, traverse evidence and opposition, enforce a character budget, and log selected IDs and hashes. |

## Initialize and use a private store

From an engine checkout with Python 3.11 or later:

```powershell
python -m kernel.ctr --context D:/private-context/context init --owner your-account
python -m kernel.ctr --context D:/private-context/context ingest --file issue-event.json
python -m kernel.ctr --context D:/private-context/context index
python -m kernel.ctr --context D:/private-context/context search "memory retention" --budget 6000
python -m kernel.ctr --context D:/private-context/context show wound:minimality-vs-ecology
```

The explicit --context path must be outside the public engine checkout; ignored
.ctr/ is allowed for local tests. init refuses personal stores in Actions when the
repository visibility is public. The private workflow also checks the live GitHub
repository visibility before accessing data.

context/state.json is authoritative. One directory lock serializes writers; a
single atomic replacement commits the changed records and hash-chained audit
together. Generated INDEX.md, graph.json, records/, SELF.json, SELF.md, and
trace_ledger.jsonl are projections. Regenerate them with index after an interrupted
export. Never edit projections directly. A stale writer lock after a killed process
requires checking that no writer remains before removing that lock.

The context hash covers records, not generated indexes or SELF files, so rebuilding
the index does not create a self-referential hash loop. Record and chain checks
detect mismatches; they are not signatures against a party capable of rewriting
the entire store and its history.

## Context and graph contract

A record has an id, kind, layer, status, title, body, sources, actor, tags, read_when,
relations, ttl_days, updated_at, review_after, and data. See
[context_record.schema.json](../schemas/context_record.schema.json).

Layers are rules, current, decisions, evidence, relations, and residues.
Relations are addresses, supports, contradicts, supersedes, depends_on, and
derived_from. Missing targets are rejected. Supersession connects records of the
same kind. Context search excludes rejected, superseded, and composted records by
default; --include-inactive explicitly includes them. Expired records carry a
review flag rather than becoming silently authoritative or being deleted.

Search uses documented lexical matching and two graph hops, not embeddings or
LLM intent inference. It returns whole records within 256..32000 characters,
not an estimated token limit. If relevant records do not fit, their IDs appear in
excluded_by_budget. Retrieval logs hash the query instead of storing its raw text,
and record the selected record hashes and context version.

A record's actor is declared attribution. It is not proof that a human approved
an assistant proposal. Accepted decisions preserve their actual declared actor.
A read-only GitHub connector cannot automatically write retrieval traces; report
the selected IDs/hashes in the task output or submit a separate recording PR.

## Wounds and decisions

```powershell
python -m kernel.ctr --context D:/private-context/context transition wound:minimality-vs-ecology investigating
python -m kernel.ctr --context D:/private-context/context decide --file decision.json --accept
python -m kernel.ctr --context D:/private-context/context transition wound:minimality-vs-ecology scarred --decision decision:retention --evidence experiment:REPLACE_WITH_ID
```

A decision declares id, title, choice, at least two rejected alternatives, cost,
failure_condition, sources, actor, evidence record IDs, and axes. axes maps null,
existential, fudo, shadow, transparency to boolean veto values. Acceptance requires
five explicit false vetoes and existing experiment/evaluation evidence. These
values are the reviewer's declared judgment, not independent model evaluations.
Changing an accepted decision requires a new ID and a supersedes relation.

A new source revision after a scar reopens the wound as recurring. Identical
deliveries are no-ops. Previously unseen older observations add history without
falsely reopening a scar. A recurrence is a review signal, not proof of a repeated bug.

## Experiments and forgetting

```powershell
python -m kernel.ctr --context D:/private-context/context experiment --repo D:/your-reviewed-project --file plan.json --trust-code
```

Plans follow [experiment_plan.schema.json](../schemas/experiment_plan.schema.json).
Declare kind (counterfactual or forgetting), title, acceptance text, wounds,
context_ids, suite, timeout_seconds, and 2..4 variants. The first variant is named
baseline. Each variant has name and ref; counterfactual variants may also have
bounded data-file edits, and forgetting variants have omit lists of memory IDs.
An optional hypothesis ID connects a trial to its proposed Dream.

required_pass declares before execution which variants must pass. It defaults
to all variants. Forgetting always requires all variants, a passing baseline,
identical code, and fewer context bytes. Tests read the selected snapshot JSON
from CTR_EXPERIMENT_CONTEXT. Use meaningful tests that exercise that snapshot.

The command is fixed to Python unittest discovery. All variants must have the
same test-suite hash and at least one executed test. Data edits cannot alter tests,
Git configuration, workflows, executable Python, or paths outside the worktree.
Time is bounded to 300 seconds of declared trial time per plan. No trial can
delete production memories. Passing omission sets are evidence for a later
retirement decision, not proof of a globally minimal context.

The --trust-code flag acknowledges that repository tests execute code. Git
worktrees isolate file changes, not the OS or network. Child processes receive a
small environment allowlist without GitHub/model tokens, but untrusted test code
still needs an external sandbox. Trials should not spawn persistent descendants.
No generated hypothesis automatically becomes executable code.

## Dream, assessment, and retirement

```powershell
python -m kernel.ctr --context D:/private-context/context dream wound:minimality-vs-ecology --seed 42
python -m kernel.ctr --context D:/private-context/context propose-dream --file model-proposal.json
python -m kernel.ctr --context D:/private-context/context assess --repo D:/ctr --file examples/evolution/judge_corpus.json --trust-code
python -m kernel.ctr --context D:/private-context/context review-dream hypothesis:REPLACE_WITH_ID accepted --decision decision:retention
python -m kernel.ctr --context D:/private-context/context compost memory:retired --decision decision:retention
```

External proposals declare title, question, experiment, acceptance_criterion,
experiment_kind, wound, source_ids, actor, and generation (provider, model,
prompt_hash). The engine records an output hash and source relations. The provider
metadata is externally declared, not independently verified. No API key or paid
model is required for the built-in template generator.

An assessment corpus declares ref, label_source, and 2..8 cases with data-file
edits and expected_vetoes for all five axes. The real agents run for every case.
Results are confusion counts and false-veto/miss rates; a missing positive or
negative denominator is null. This measures the declared corpus only, not general
semantic judgment. To test an assessment-type hypothesis, also declare hypothesis
and wounds in the corpus.

Retirement keeps the record and its history but excludes it from ordinary
retrieval. TTL is a review date, not automatic removal. Restoring a retired design
uses a new record and a new evidence-backed decision.

## GitHub and connected AI clients

[templates/personal-context](../templates/personal-context) contains the private
repository starter. Replace CTR_ENGINE_REVISION with a reviewed 40-character
public engine commit, never a moving branch. Personal Issue ingestion, inbox
processing, generated state, PRs, and artifacts all run in the private repository.
The workflow refuses public visibility. It never sends personal data back to the
engine repository.

Codex, ChatGPT Work, and ChatGPT can use whatever GitHub connector permissions
their environments provide. Read README, AGENTS, and context/INDEX first. Follow
the graph to actual record files. Write proposed memories/rules or externally
generated hypotheses to inbox/ through a PR. Do not claim an external connection
is installed or authorized merely because this template exists.

Nightly Dream work proposes at most three least-recently-considered active wounds
on dream/context-cycle. Other updates use codex/context-cycle. Neither is
automatically merged. Manual experiment and assess runs accept reviewed plan
filenames from plans/. Local CLI also supports other reviewed project checkouts.

The workflow queues up to 100 waiting runs and resumes the open candidate PR's
validated state before processing a new event. If main and a candidate have
divergent context histories, it stops instead of overwriting either history.
Merge or reconcile that candidate before processing a conflicting branch.
Queue overflow and failed runs must be inspected; GitHub is not an unlimited
event-delivery service.

## Reproducible proof

```powershell
python -m unittest
python -m kernel.evolution_demo --output D:/fresh-ctr-demo
```

The demo constructs an isolated synthetic Git repository and records a rejected
alternative that fails, redundant memory omission that passes, essential memory
omission that fails, evidence-backed Dream adoption, a scar and recurrence,
five-axis assessment, and graph retrieval. summary.json reports each condition.
Use a fresh output directory per run. CI runs this proof without personal data.
