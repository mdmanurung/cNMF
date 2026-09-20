# Feature contract — C (one contribution per run per consensus program)

Status: FROZEN at P3-01 (v1.1) — hypothesis, rule, endpoints, margins and
comparisons fixed below; changing any after seeing a C-ON comparison row
creates a new protocol version
Protocol version/hash: v1.1, `cc5241076a6c3e5f98b7575f0b09b12337c119e6ddaea685514692ebc9d42ec9`
Code/environment revision: harness P3-01, upstream `5dbc5baaa0b9079b55bce554d801caa235a50457` (`src/cnmf/**` unmodified)
Evidence tier: NONE for adoption. SMOKE + DEVELOPMENT A-OFF/C rows exist and inform design only.

## Hypothesis and exact rule

Upstream consensus takes the median over every spectrum in a cluster. When one
optimizer run splits a true program into two near-identical factors, both land
in the same cluster and that run votes twice; C gives each run one vote per
cluster. One-pass run-aware deduplication (`features.consensus_spectra_from_bank`,
`one_per_run=True`): per (run, upstream cluster) pair, keep the member with the
smallest L2 distance to its cluster's centroid (**centroid-nearest, frozen
here** — this resolves D015's open item on the ablation plan's side: the plan
now fixes the rule rather than merely naming the shape).

Everything else is unchanged: upstream factor normalization, density filtering,
initial clustering, median summary, output ordering, final refit. The mean of a
run's contributions as its single vote is a legitimate alternative and is
recorded as a **deferred sensitivity, not this feature** — implementing it to
rescue a result would repeat what P1 refused to do for A.

## Pilot facts that shape the comparisons (all pre-existing rows)

- C fires **only above K_true** (DEVELOPMENT: 27/41 cluster-corrections in 001/011,
  all at K∈{8,9,10}; SMOKE: 1/12). At K_true=7, C-ON ≡ C-OFF bitwise
  (000==001, 010==011 on every endpoint, both folds) — the no-op property,
  which P3-03 asserts as a test rather than observing again.
- Consequence: the primary C comparisons run at **fixed K>K_true** (8, 9, 10),
  where the constraint can bind, before any end-to-end reading. There is no
  selected-rank C while A is dropped (no operative selector).

## Comparisons (fixed rank; identical factor banks)

- `000` vs `001` (full pool), `010` vs `011` (matched budget, same draw):
  same cells → same `s_g` → **training-scale primary is valid** (unlike B).
- Both arms load the IDENTICAL `merged_spectra` bank (same discovery cells,
  K, seeds, convergence limits, failure handling); P3-04 asserts equal
  `factor_bank_hash` per (fold, K) pair and refuses the comparison otherwise.
- `100/101`, `110/111`: omitted — A is dropped and its selector overselects,
  so those cells would measure A's harm, not C (same rationale as B, D041).
- Corruption fixtures (P3-04): deliberately injected duplicate factors validate
  mechanics; `C_duplicate_merge` end-to-end runs must show the practical gain;
  `C_separated` is the no-harm control.

## Endpoints and margins (frozen P2-style on the same tier scales)

| Role | Metric and exact definition | Direction | Decision margin | Evidence used to set margin |
|---|---|---|---|---|
| Primary | `heldout_squared_prediction_error_v1`, equal-donor mean (training scale — shared, same cells) | Lower (001 vs 000, 011 vs 010) | **30** | Same tier/endpoint scale as A's margin (donor SE 10.45 → 3×SE): the SE is a property of the tier, not the feature; re-deriving it per feature would be tuning constants to each comparison |
| Safeguard: recovery | `program_recovery_cosine_v1` + matched null | Higher | **max harm 0.01** | As A/B (experiment SE 0.0008, thin n=2, stated) |
| Safeguard: usage | `usage_error_v1` | Lower | **max harm 0.05** | As A/B (3×SE 0.032, rounded up) |
| Safeguard: cost | `wall_seconds_v1` | Lower | **5× paired wall** | C adds no fits (same banks, one aggregation pass); as B |
| Aggregation provenance | retained/omitted counts, distinct contributing runs, effective nonempty rank | — | **reported, not margined** | Never silently replace a failed fit or drop an empty component (`consensus_info`) |

**Adoption rule:** KEEP requires a worthwhile prediction gain or recovery gain
at K>K_true in `C_duplicate_merge` with no safeguard breached and no-op
confirmed at/below K_true; else DROP (no CONDITIONAL scope is pre-registered —
a regime-gated C would need its own activation rule written before seeing the
rows, and none is).

## Regimes (P3-04)

`base_identifiable` (C rarely fires — measures the no-op) →
`C_duplicate_merge` (target: `marker_overlap_fraction=1/3`, `lambda_separation=2.5`)
→ `C_separated` (no-harm control). Corruption fixtures in `test_features.py`.
