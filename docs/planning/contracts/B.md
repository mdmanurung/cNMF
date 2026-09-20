# Feature contract — B (donor-balanced discovery)

Status: FROZEN at P2-01 (v1.1) — hypothesis, units, endpoints, margins, sampling policy and anchor fixed below; changing any after seeing a B-ON row creates a new protocol version
Protocol version/hash: v1.1, `cc5241076a6c3e5f98b7575f0b09b12337c119e6ddaea685514692ebc9d42ec9`
Code/environment revision: harness `1064712`, upstream `5dbc5baaa0b9079b55bce554d801caa235a50457` (`src/cnmf/**` unmodified)
Evidence tier: NONE for adoption. SMOKE + DEVELOPMENT A-OFF evidence exists and informs design only.

## Why this file exists now, before the DEVELOPMENT factorial is read

The SMOKE factorial was already written up in
`docs/benchmarks/registry/p0-04_features_bc_smoke.tsv` when an audit of the B arm found that
**every one of B's three reported numbers depends on a units convention that nobody chose.**
One of them reverses sign under the other convention. The correction is in that file; this
file exists so the convention is fixed *by pre-registration* rather than picked afterwards
from whichever route makes B look better.

Writing it now, while the DEVELOPMENT rows are still being generated and before any of them
has been read, is the only moment at which that claim is checkable.

## The measurement problem this contract resolves

Feature B changes **which cells are handed to `cnmf.prepare`**. `prepare` then computes its
own per-gene scale internally, from exactly the cells it received:

```python
# src/cnmf/cnmf.py:542 — may not be modified
norm_counts.X /= norm_counts.X.std(axis=0, ddof=1)
```

So `s_g` is downstream of B's sampling rule **by construction**, and the dictionary, the
transform and every loss live in that `s_g`-scaled space.

### What `hold_preprocessing_constant_across_B: true` can and cannot mean

`docs/benchmarks/configs/ablation_plan.yaml:32` requires preprocessing held constant across B.
PROTOCOL §3.2's preprocessing is the pair `{G, s_g}`. Measured, on `outer_0` at SMOKE:

| component | held constant across B? | how |
|---|---|---|
| `G` (gene panel) | **yes**, verified byte-identical | selected once on the full training pool, frozen into both arms via `prepare(genes_file=...)` |
| `s_g` (per-gene scale) | **no, and it cannot be** | computed inside `prepare` from the cells it is given |

The `s_g` half is **not satisfiable** under this programme's constraints. The two routes to
satisfying it both fail:

1. *Fit `s_g` on the full training pool and use it for scoring.* The dictionary would still
   live in the sample's scale, so `verify_transform_matches_cnmf` would fail — correctly. The
   scoring transform would no longer describe the cells that were actually factorized.
2. *Make `prepare` accept an externally supplied scale.* Requires editing `src/cnmf/**`,
   which is forbidden outright.

**Measured drift**, B-ON vs B-OFF, `outer_0`, over |G| = 100 genes:
`min 0.809 / p05 0.935 / median 1.043 / p95 1.161 / max 1.238`; mean |log2 ratio| 0.091
(≈ 6.5% typical); 1 gene of 100 moves more than 20%.

### Why that is not a small problem

A ~6.5% per-coordinate scale drift is not a rescaling of the comparison — it is a **shear**,
the same class of error D013 recorded for the count/scaled confusion. Measured on the SMOKE
rows, all three of B's endpoints move with it:

| endpoint | effect of reading B in the arm's own scaled space |
|---|---|
| held-out predictive error | **sign of the B effect flips in 4 of 6 (fold × rank) cells** |
| `program_recovery_cosine_v1` | no sign flips; magnitude up to 3.5× different (k=3: −0.0019 → −0.0066) |
| `usage_error_v1` | the Hungarian **alignment itself** differs at k=4 `outer_0`; B-OFF moves 0.7246 → 0.9846 |

## Endpoints, and the units they are defined in

**Primary endpoint.** `heldout_squared_prediction_error_counts_v1`, equal-donor mean, lower
better. Count units, not the engine's scaled space.

**Secondary endpoints.** `program_recovery_cosine_v1` and `usage_error_v1`, both scored with
**truth in count space and the fitted dictionary pulled into count space** via
`Spectra.to_count(s_g)` — never with truth pushed into an arm's own scaled space.

**The rule, stated once so it covers endpoints not yet named:** any quantity compared *across
B arms* is expressed in count units, because count space is the only reference the two arms
share. `heldout_squared_prediction_error_v1` (scaled space) remains a valid within-arm
diagnostic and is not withdrawn; it is simply not a cross-arm endpoint.

**This choice is on invariance, not on the numbers, and it does not flatter B.** In count
units B's predictive error gets *worse* in 4 of 6 cells where the scaled reading had it
improving in 3; at k=4 `outer_0` the count-route alignment makes B's usage-error advantage
*larger*. The convention was picked because it is the same for both arms, and it moves the
result in both directions.

## The residual this does NOT remove, and must not be claimed to

Count-unit *reporting* removes the units artifact from the comparison. It does **not** make
the two arms the same estimator. The inference-time NNLS solves

```
u = argmin_u || x_test[:, inf] - u · V[:, inf] ||²   with everything in that arm's 1/s_g scale
```

so each arm's usages are recovered under its own per-gene weighting. Two arms with identical
programs would still produce slightly different `u`. That residual is **arguably part of what
feature B does in deployment** — a practitioner running donor-balanced discovery gets the
donor-balanced scale too — but it is a property of the intervention, not a controlled
comparison, and no B result may be reported as if it had been controlled for.

## Margins (frozen P2-01 on DEVELOPMENT 000 controls, K_true=7)

| Role | Metric and exact definition | Direction | Decision margin | Evidence used to set margin |
|---|---|---|---|---|
| Primary | `heldout_squared_prediction_error_counts_v1`, equal-donor mean (count units — the only shared reference, §units above) | Lower (010 vs 000) | **70** (count units) | 3× donor-level SE (22.88, n=48 donor-rows) in DEVELOPMENT 000 controls; mean 945, so ~7% — same relative scale as A's margin by construction, not by copying |
| Safeguard: program recovery | `program_recovery_cosine_v1` in count space, beside matched null | Higher | **max harm 0.01** | Same basis as A (experiment SE 0.0008 on n=2 folds — thin, stated); small vs the 0.15 fit–null gap |
| Safeguard: usage | `usage_error_v1` | Lower | **max harm 0.05** | 3× experiment SE (0.0106 → 0.032), rounded up |
| Safeguard: subgroup preservation | B_context rare-program recovery | Higher | **NOT_SET — no rare-program metric exists** | Blocks adoption on this safeguard until defined (same rule as A); P2-05 may close CONDITIONAL on the imbalanced regime with INCONCLUSIVE on context, never by inventing comparability |
| Safeguard: cost/failures | `wall_seconds_v1`, `failed_fits_v1` | Lower | **5× the paired 000 wall** | B draws the same cell budget through the same fits, so cost should be ~1×; 5× sits above observed ±40% BLAS noise (D024) and below absurdity. Tighter than A's 25× because B adds runs, not fits |

**Observed pilot B effect (not a result):** at K_true=7 on balanced DEVELOPMENT
controls, 010 vs 000 differs by +1.8/+1.9 count units (~0.2%, far below margin
70) — expected, since with `cells_per_donor_cv=0` equal-per-donor and
proportional draws are near-identical. `base_identifiable` is therefore B's
**no-harm control**, not its target regime; the target is `B_imbalanced`.

## Frozen sampling policy

- **Budgets:** one total cell budget per tier/scenario, identical across arms
  (SMOKE 72, DEVELOPMENT 1440 — the existing factorial budgets; A-pair budgets
  ab48/ab960 are a separate comparison and stay out of B rows). B-OFF draws
  `proportional_without_replacement`, B-ON `equal_per_donor_without_replacement`.
- **Replicates:** 3 sampling replicates per arm (r=0,1,2). Replicate r uses
  `sampling_seed = base + r` and `variant: rep{r}` (variant distinguishes the
  `experiment_id`s, D014 pattern — the seeds dict in the id is untouched so
  existing ids never move). The draw's variance is reported across replicates,
  never assumed negligible (this closes fence item 2 of §"What would have to be
  true" above).
- **Redistribution rule:** the implemented shortfall redistribution (donors
  below equal share contribute all cells, remainder redistributed over donors
  with spare cells; `features.discovery_sample`) is blessed as the frozen
  policy — deterministic given seed, arms always exactly budget-matched
  (asserted, not assumed). Closes fence item 3 without touching frozen files.
- **Shared preprocessing:** G frozen once per fold on the full training pool
  via `prepare(genes_file=...)`, byte-identical across arms (verified, D016);
  `s_g` drifts by construction and all cross-arm endpoints stay in count units.
- **Discovery set frozen** across ranks and optimizer seeds within an
  experiment; sampling varies only through the replicate index.
- **Full-data anchor:** one `000` run per tier/scenario with no discovery
  section (`arm: full_training_pool`, every training cell) — the practical
  anchor. The matched-budget 000 is the controlled comparator; the two are
  never averaged or interchanged (D010).

## Regimes (P2-04)

`base_identifiable` (no-harm control: B should change nothing) →
`B_imbalanced` (target: `cells_per_donor_cv=0.8`, B should improve recovery) →
`B_balanced` (matched control, cv=0) → `B_context` (subgroup preservation
safeguard). The latter three scenarios are `implemented=False` today; P2-02
implements them in the simulator (generative parameters only — no inference
change, no protocol change).

## What had to be true for B to be adopted (P2-01 discharge)

1. ✅ Margin on count-unit prediction: **70**, frozen above.
2. ✅ Sampling replicates: 3/arm frozen in sampling policy above (P2-02 builds them).
3. ✅ Redistribution rule frozen above (implemented rule blessed, arms exactly matched).
4. ✅ Cross-arm audit: G identical asserted; `s_g` drift reported (median 1.04, max 1.24), never asserted away — plus v1.1 §3.4 settles the primary-loss scope.

Remaining NOT_SET: subgroup-preservation margin (no metric exists — see margins table).
