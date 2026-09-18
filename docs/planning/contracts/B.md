# Feature contract — B (donor-balanced discovery)

Status: DRAFT — endpoints named and their *units* fixed; margins still NOT_SET
Protocol version/hash: v1.0.1, `715639895663bc74e7b864bc1cfae60c2fcd05b013e25f23016d45e86f4f9ca5`
Code/environment revision: harness `328238e`, upstream `5dbc5baaa0b9079b55bce554d801caa235a50457` (`src/cnmf/**` unmodified)
Evidence tier: NONE for adoption. SMOKE evidence exists and is INCONCLUSIVE by construction.

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

## Margins

`NOT_SET`, all of them. No adoption decision may cite any B number until they are set, and
they may not be set after seeing a confirmation result. `smoke_can_promote_feature: false`.

## What would have to be true for B to be adopted

Named here so the bar is visible before the evidence is:

1. A pre-registered margin on `heldout_squared_prediction_error_counts_v1`.
2. Sampling replicates, so the draw's own variance is reported rather than assumed
   negligible — currently a single draw per arm, which is why SMOKE is INCONCLUSIVE and not
   "no effect". See `features.discovery_sample_b` in `cnmfbench/provisional.py`.
3. The redistribution rule for donors holding fewer cells than their equal share either fixed
   in the ablation plan or shown not to change the B effect.
4. A cross-arm audit asserting `G` identical and **reporting** the `s_g` drift rather than
   asserting it away — the assertion in the fence entry's `hardening_requires` cannot be met
   as written and is superseded by this file.
