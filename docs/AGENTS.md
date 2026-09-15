# Agent instructions: incremental cNMF development

Merge these instructions with existing repository instructions; do not overwrite unrelated guidance. The full implementation contract is in `IMPLEMENTATION_PROMPT.md`.

## On entering a session

1. Read repository instructions, `planning/PROGRESS.md`, the current gate, and the active feature contract.
2. Inspect the worktree and preserve unrelated changes.
3. Select the next dependency-ready task; start with S0 and P0, not all features together.
4. Record the task as IN_PROGRESS before substantive edits.

## Scope

Preserve upstream cNMF defaults and outputs. The first cycle contains only:

- A: donor-blocked, observation-separated predictive rank selection.
- B: donor-balanced discovery, tested against proportional sampling at the same cell budget.
- C: one contribution per optimization run per consensus program, using the same factor bank and all other upstream aggregation choices.

Every switch must work independently. Reporting, tests, and provenance are shared infrastructure, not additional interventions. Do not add NB/Poisson solvers, multiresolution graphs, multimodal models, new sparsity penalties, new feature selection, or new batch correction in this cycle.

## Scientific integrity

Use training-only preprocessing. Keep all observations from one donor in the same donor fold. Estimate test usages from an inference panel, then score unused observations; never normalize with a held-out total or refit spectra on test cells. Do not treat omitted entries as observed zeros.

Freeze the discovery-cell set across K and seed runs. For B comparisons, preprocessing and total cell budget remain identical. For C comparisons, raw factor-bank hashes must match. Distinguish the matched-budget baseline from the full-data legacy anchor.

Record failed and negative experiments. Do not change thresholds after seeing confirmation results. Smoke tests establish execution, not scientific benefit. A correct feature may be dropped or left conditional; do not force a positive conclusion.

Use full-loading matching with missing/extra penalties, aligned usage error, held-out prediction, and total compute/failure costs. Do not use ARI or visual appearance as the main program-recovery metric.

## Implementation

Prefer small changes, typed/tested functions, and stable cNMF APIs. Keep comparator dependencies optional. Use scripts for heavy computation, Snakemake for orchestration, and local/SLURM profiles with explicit resources. Avoid dense cell-by-cell matrices, uncontrolled BLAS oversubscription, and unvalidated cache reuse.

Do not push, publish, open pull requests, force-reset, or delete unrelated user files without authorization. Pin reference sources and inspect licenses before reuse. Do not fabricate hashes, test outputs, citations, or completed jobs.

## On leaving a session

Update PROGRESS.md, experiment records, gate/decision evidence, and the next-task handoff. A task is DONE only with its required acceptance evidence. Keep software status, scientific adoption, and evidence tier separate. State exact commands actually run, exit codes, artifact paths, blockers, and the next action; never imply asynchronous continuation.
