# First-cycle evidence report (local, 2026-09-19)

Scope: incremental cNMF benchmark — P0 baseline, features A (predictive rank
selection), B (donor-balanced discovery), C (run-aware consensus). Protocol
v1.1 (`cc524107…`), harness at cycle head, upstream `5dbc5ba` unmodified.
No remote publication; SLURM profile NOT_RUN_ON_SLURM.

## Recommendation

**Use original unmodified cNMF (all features OFF).** A, B and C were each
DROPPED at DEVELOPMENT simulation scope, by pre-registered margins, with
mechanisms recorded. Negative/conditional results are valid outputs
(IMPLEMENTATION_PROMPT §13); no fourth feature was introduced to avoid that.

## What was found, per feature (gates/P0.md, P1.md, P2.md, P3.md)

- **A — DROP.** Min-loss donor-blocked selection overselects to the grid edge
  in 3/4 folds (no parsimony pressure on flat inner curves); prediction never
  improves (best Δ 0.0 vs margin 30); recovery/usage harm in 3/4 folds. The
  silhouette baseline found K_true in 2/2 base folds. 1-SE variant named, unbuilt.
- **B — DROP.** Equal-per-donor ≡ proportional at 24-donor scale on every
  endpoint (|Δ|≤3.1 vs margin 70; recovery/usage overlap; cost ~1×), including
  the imbalanced target. Draw variance ~0.2%. Real-data scale untested either way.
- **C — DROP.** Safe no-op where the constraint holds (bitwise at/below K_true);
  never improves prediction above it (12/12 ON≥OFF, ≤+2.8 vs margin 30);
  safeguards pass. Mean-vote alternative deferred.
- **Interactions:** B×C negligible (|I|≤2.5 vs 70); A-interactions unavailable
  by design (would confound with dropped-A harm or sample size).

## Methodological byproducts (kept regardless of verdicts)

Donor count (not leakage) drives the blocked-vs-random gap (D008, t=+4.30 vs
−0.37); unit-tagged spectra and count-unit cross-arm endpoints (D013, D016);
content-keyed cache with atomic sentinels; the fence-as-code pattern (now empty);
GeneNMF smoke adapter (R4_51); Kang-2018 labelled-activity diagnostic
(interferon AUC 0.91–0.95 — pipeline works on real input, promotes nothing).

## Explicit limits (unsupported claims)

No biological generalisation (Kang is a diagnostic; sealed tier untouched by
decision, not by oversight); no rare-program bounds (metric absent);
no real-data-scale B claim; no comparator comparison (no gene-set metric);
upstream suite 36/38 with two named scale-blind expected failures (D044, one
open question: P0-01's PBMC-bitwise non-reproduction after full elimination);
feasibility NO-GO ×2 stands (variance, not absence).

## Provenance

Tracked: RESULTS.tsv / EXPERIMENTS.tsv (all `ok_provisional` historically —
correct, fence-produced; now fence-empty), registry TSVs, gates, DECISIONS
D000–D044, frozen configs. `src/cnmf/**` byte-identical to pinned upstream
throughout. Reproduce: `python -m pytest cnmfbench -q` (290 green);
`python -m cnmfbench.skeleton --config docs/benchmarks/configs/<name>.yaml`.

## Resumable handoff

Re-entry only through new decisions: real-data B at hundreds of donors,
the 1-SE A variant, or the mean-vote C sensitivity — each needs its own
pre-registered contract before any row is written. Nothing here may be
reopened by re-reading old rows.
