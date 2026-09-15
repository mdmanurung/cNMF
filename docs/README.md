# cNMF incremental-development prompt bundle

Prepared 15 September 2026. This bundle is an implementation specification and planning scaffold, **not an implemented cNMF fork or an executed benchmark**.

## Start

Place these files in the target cNMF checkout or fork, preserving existing files and merging `AGENTS.md` rather than overwriting it. Give `IMPLEMENTATION_PROMPT.md` to the coding agent as its task. Start at S0 and P0; do not request all features in one implementation pass.

A suitable launcher message is:

> Read IMPLEMENTATION_PROMPT.md and the repository instructions. Use planning/PROGRESS.md as the persistent tracker. Start S0 and P0 only; keep upstream behavior unchanged, execute available tests, and update progress with evidence. Do not implement A, B, or C until the P0 readiness gate is documented.

For subsequent sessions:

> Read the current progress, gate, and decision records, then continue the next dependency-ready task. Preserve the A/B/C ablations and record tests, failures, and scientific decisions before ending the session.

## Files

| File | Role |
|---|---|
| `IMPLEMENTATION_PROMPT.md` | Complete scientific/engineering instructions and reference sources |
| `AGENTS.md` | Persistent operating rules for coding agents |
| `planning/PROGRESS.md` | 31 initialized tasks, dependencies, gates, ablation status and session handoff |
| `planning/FEATURE_CONTRACT_TEMPLATE.md` | Prespecified hypothesis, controls, metrics and decision margins |
| `planning/GATE_TEMPLATE.md` | Separate software correctness and scientific adoption assessment |
| `planning/DECISIONS.md` | Append-only design and scientific decision history |
| `benchmarks/EXPERIMENTS.tsv` | Empty execution registry with provenance and failure columns |
| `benchmarks/RESULTS.tsv` | Empty per-unit tidy metric registry |
| `benchmarks/configs/ablation_plan.yaml` | Eight A/B/C configurations plus separate anchors and validation rules |
| `benchmarks/configs/smoke.yaml` | Proposed small smoke settings, not scientific evidence or current executable software |
| `SHA256SUMS.txt` | Integrity checksums of the bundle files |

> **Annotation added 2026-09-15 (S0-03), not part of the original bundle.**
>
> Two discrepancies between this table and the checkout, recorded rather than silently fixed:
>
> 1. **`SHA256SUMS.txt` was never shipped.** No such file exists anywhere in this repository. The
>    bundle's integrity was therefore never verifiable from within it. No replacement has been
>    generated, deliberately: the bundle is actively changing as the programme runs, so a checksum
>    file written now would certify the current working state rather than the delivered one, which
>    is the opposite of what the row promises. Per-file provenance that *is* trustworthy lives in
>    `benchmarks/registry/` (environment locks, test-data manifest) and in `planning/PROGRESS.md`.
> 2. **Paths in this table are bundle-root-relative and no longer match the tree.** Decision D001
>    kept the planning bundle under `docs/`, so every `planning/…` and `benchmarks/…` path above
>    reads `docs/planning/…` and `docs/benchmarks/…` in this checkout. The same applies to the
>    launcher message above and to the layout block in `IMPLEMENTATION_PROMPT.md:69`. New
>    executable trees go at the repository root, not under `docs/`.
>
> Files added since the bundle was written: `planning/PROTOCOL.md` (S0-03, frozen benchmark and
> selection rules) and `benchmarks/registry/` (P0-01 evidence).

The new command interface, workflows, tests and modules described by the prompt must still be implemented. Null source pins and scientific margins are intentional: the agent must resolve and preregister them, not invent them. Original legacy cNMF commands remain the compatibility anchor.

## First cycle

P0 reproduces upstream and validates the measuring system. P1 changes rank selection only. P2 changes donor sampling only, at matched cell budgets. P3 changes contribution weighting within existing consensus clusters only, reusing the same factor bank. Full factorial and fixed-rank controls separate standalone gains, incremental gains, and interactions.

A technically correct feature can be KEEP, CONDITIONAL, DROP or INCONCLUSIVE scientifically; the best-supported configuration may remain the baseline.
