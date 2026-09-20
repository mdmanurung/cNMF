# PROTOCOL — frozen benchmark and selection rules

`protocol_version: 1.2`
`hash_convention_version: 1`
`metric_definition_version: 2`
State: **FROZEN** (see §9 for what "frozen" permits and forbids)
Pinned upstream: `dylkot/cNMF` @ `5dbc5baaa0b9079b55bce554d801caa235a50457` (cNMF 1.7.1)

This file defines the names that `docs/benchmarks/configs/*.yaml` reference but nothing in the
repository defines. It fixes **rules**, not numerical margins. Feature hypotheses live in
`contracts/{A,B,C}.md`; adoption verdicts live in `gates/*.md`; margins live in contracts.

Everything here is a **benchmark surrogate** unless explicitly attributed to upstream cNMF. The
upstream algorithm is not modified by this programme; A, B and C are harness-side switches.

---

## 0. Scope and reading order

| § | Defines | Referenced from |
|---|---|---|
| 1 | `preregistered_training_only_baseline_surrogate` | `ablation_plan.yaml: inactive_A_selector` |
| 2 | `delta` policy (null until P1) | this file |
| 3 | `transform: training_fitted_and_leakage_audited`, `nonnegative_least_squares_frozen_dictionary`, `training_scale_squared_prediction_error`, `equal_donor_mean` | `smoke.yaml: validation`, `ablation_plan.yaml: validation` |
| 4 | `fixed_gene_panels` | `ablation_plan.yaml: within_test_donor_split` |
| 5 | `metric` / `metric_definition_version` vocabulary | `RESULTS.tsv` |
| 6 | data contract | Session 2 simulator; P0-02 validates |
| 7 | hash convention | `EXPERIMENTS.tsv` provenance columns |
| 8 | out of scope | — |
| 9 | amendment rules | — |

Background for anything below: `SOURCE_AUDIT.md` §1.2 (cNMF dataflow — three distinct spectra
normalizations, two std pipelines) and §1.5 (measured determinism, declared tolerance).

---

## 1. `preregistered_training_only_baseline_surrogate`

The rank-selection rule used whenever **feature A is OFF**. Feature A is measured against it, so
it must be a fair opponent: auditable, deterministic, and computed from training information only.

**This is a benchmark surrogate, not an official upstream algorithm.** Upstream cNMF provides a
stability–error *inspection* workflow, not one prescribed automatic selector
(`Stepwise_Guide.md:85`; `IMPLEMENTATION_PROMPT.md:196`). Any statement of the form "cNMF selects
rank by…" is false and must not appear in a report produced by this programme.

### 1.1 Inputs

Both inputs already exist on disk after a rank sweep; the selector computes nothing new.
`k_selection_plot` (`cnmf.py:1119-1158`) calls `consensus(skip_density_and_return_after_stats=True)`
per K and saves a DataFrame to the `k_selection_stats` path with **four** columns
(`cnmf.py:932-934`):

- `k` — candidate rank
- `local_density_threshold` — the argument **as passed**, not a description of what happened.
  In this branch `consensus` overrides `density_threshold_str = '2'` (`cnmf.py:876-877`) and
  applies no density filtering. The selector does **not** read this column; it is named here
  only so a future session does not mistake it for a record of the filtering actually applied
- `silhouette` — stability, **higher is better**
- `prediction_error` — in-sample reconstruction error, **lower is better**

`prediction_error` is recorded but **is not used by the primary rule**. It is typically monotone
decreasing in K, so any selector using it alone would always return the largest grid value.

Only ranks in the configured `candidate_ranks` grid are eligible. The grid comes from the run
configuration and is frozen before the run (§9).

### 1.2 Primary rule — largest-among-stable

    K* = max { K in grid : silhouette(K) >= max_{K' in grid} silhouette(K') - delta }

In words: find the most stable rank on the grid; keep every rank whose stability is within `delta`
of it; take the **largest** such rank.

**Why largest, not argmax.** Upstream's documented practice is "the largest value that is
reasonably stable and/or a local maximum in stability" (`Stepwise_Guide.md:85`) — *largest among
stable*. This distinction is load-bearing for the whole P1 comparison. On the common curve shape
where silhouette sits near 1.0 and decays slowly across small K, plain `argmax` returns the
smallest grid value almost every time. A baseline that effectively always selects K=2 would
systematically under-select rank, feature A would beat it trivially, and the `000` vs `100`
comparison would measure nothing. Freezing the rule in the *largest-among-stable* form before any
comparison is run is the safeguard against that.

### 1.3 Sensitivity heuristic (reported, never substituted)

Required by `IMPLEMENTATION_PROMPT.md:196` ("a second simple training-only heuristic as a
sensitivity check"):

    K*_sens = min { argmax_{K in grid} silhouette(K) }    # ties -> smaller K

Reported alongside `K*` in every run where a rank is selected. It is **never** silently
substituted for `K*`, and a divergence between the two is a reportable finding, not a bug.

The two rules bracket the parsimony/complexity axis. Neither requires reconciling the silhouette
and error curves onto a common scale, and neither introduces a weighting parameter.

### 1.4 Frozen behaviours

These four are named explicitly by `IMPLEMENTATION_PROMPT.md:196` and are frozen here.

| Situation | Behaviour | Flag set on the row |
|---|---|---|
| **Ties** — several K satisfy the rule with equal silhouette | The rule already takes the largest K. For the sensitivity heuristic, ties resolve to the **smallest** K. | — |
| **Degenerate (flat) curve** — `max(silhouette) - min(silhouette) < 1e-6` over the eligible grid | Declare degenerate. Select the **smallest** K. Do not apply `delta`. Note the ordering rule below: the null-`delta` refusal is checked *first*, so this branch is never a way to obtain a rank without `delta`. | `selector_degenerate = true` |
| **Search boundary** — `K*` is the smallest or largest grid value | Select it. **Never auto-expand the grid.** | `selector_boundary = true` |
| **Failed or NaN K** — the fit did not complete, or `silhouette` is NaN | Drop that K from the eligible grid before applying the rule. Count it in `n_failed_units`. **Never** silently replace it with a neighbouring K. | — |

Grid expansion after seeing outer-test outcomes is **forbidden**. Expansion justified by
inner-development evidence creates a **new protocol version** and requires fresh confirmation
(`IMPLEMENTATION_PROMPT.md:215`).

If every K in the grid fails, no rank is selected: the row's `status` records the failure and
`selected_rank` is null. This is distinguishable from the fixed-rank convention in §5.3 because
`status` differs.

### 1.5 True-rank oracle

A selector that reads the simulator's true rank is permitted **only** as an explicitly labelled
diagnostic column, never as a deployable method and never as a comparator in an adoption decision
(`IMPLEMENTATION_PROMPT.md:198`). Neither the baseline surrogate nor feature A's selector may be
tuned using true simulated rank or any outer-test result.

---

## 2. `delta`, calibrated at P1-01 on development controls

`delta: 0.04812`

Set once at P1-01 (v1.1 amendment, D026/D033) by the procedure frozen below,
before any outer-test run and before any A-ON row exists. It is a **frozen
protocol constant, not a tuned parameter** and may not be adjusted afterwards
without a new protocol version.

**Calibration record.** Four optimizer seeds on `base_identifiable` and `A_weak`
at DEVELOPMENT tier; `delta` is the maximum per-(outer fold, K) silhouette
standard deviation observed (`base_identifiable outer_0, k=8`). Full curves and
dispersion table in D026; runs under `results/exploratory/p06-delta-*`
(calibration inputs, never benchmark rows). Step 4 (record before checking
selection) and step 5 (no adjustment on true rank or outer-test results) were
observed: the value was written down before `select_rank` was run on any curve.

**Enforcement history.** While `delta` was null (v1.0.1) the baseline selector
refused to run rather than fall back to a default. That refusal is spent: with
`delta` set, the selector operates. A value chosen at the point of use would
still be a value chosen after seeing the data, and remains forbidden.

**Order of checks — normative, because §1.4 would otherwise conflict with this section.** The
null-`delta` refusal is evaluated **first**, before the eligible grid is built and before any
edge case in §1.4 is tested:

    1. if delta is null            -> refuse (raise); no rank is returned
    2. drop failed/NaN K from grid -> if the grid is empty, fail the row (§1.4)
    3. if the curve is degenerate  -> select smallest K, selector_degenerate = true
    4. otherwise                   -> apply the §1.2 rule
    5. set selector_boundary if K* is a grid endpoint

This matters because §1.4's degenerate-curve branch says "do not apply `delta`". Without the
ordering above, a flat curve would be a route to a selected rank while `delta` is still null —
exactly the outcome the refusal exists to prevent. Refusal precedes rule evaluation; the degenerate
branch is a shortcut *within* the rule, not an exemption from the constant it presupposes.

**Nothing before P1 needs it.** `ablation_plan.yaml` declares
`fixed_rank_configurations: ['000','010','001','011']` — exactly the configurations where A is
OFF. All P0 work therefore runs at **fixed rank across the grid**, emitting complete fixed-rank
curves (required by `IMPLEMENTATION_PROMPT.md:196`) without invoking the selector.

**Calibration procedure, frozen now.** `delta` is set once, at the start of P1, before any
outer-test run:

1. Inputs are **development-tier** controls only (§6.4). Sealed confirmation data and every
   outer-test fold are excluded.
2. Compute silhouette curves across the candidate grid on development scenarios that include at
   least one identifiable case (`base_identifiable`) and at least one weak-signal case (`A_weak`).
3. Choose `delta` from the **within-scenario dispersion of silhouette across optimizer seeds** —
   it is a "practically indistinguishable stability" band, so it must be on the scale of the noise
   in that measurement, not on the scale of the between-K differences it will adjudicate.
4. Record the curves, the dispersion estimate and the chosen value in `DECISIONS.md`.
5. `delta` may not be adjusted using true simulated rank or any outer-test result, then or ever.

Setting `delta` creates **protocol version 1.1** with its own file hash, written into
`ablation_plan.yaml`. Changing it afterwards creates a further version and invalidates any
confirmation obtained under the previous one.

The same null-until-calibrated policy governs the `program_precision_v1` / `program_recall_v1`
threshold (§5.2), for the same reason and under the same procedure.

---

## 3. Transform, projection and loss

This section defines four of the seven names. It replaces the open question flagged in
`SOURCE_AUDIT.md` §1.2.

### 3.1 Why the TPM route is excluded

`ablation_plan.yaml` sets `test_library_total_normalization: forbidden`. The reason is leakage, not
taste: TPM normalises a cell by its **total count across all genes**, which for a held-out cell
includes the genes in its validation panel. Dividing by that total carries validation-panel
information into the inference-panel values the usages are estimated from. The magnitude of the
leak is not the point — it is not auditable, so it is not allowed.

Consequently scoring uses the **HVG-panel / `median_spectra`** route, never the
all-gene / `spectra_tpm` route. `median_spectra` is the consensus dictionary cNMF actually saves
(`cnmf.py:913-916`): component-wise median of the L2-normalized spectra, then row-sum-normalized
to 1. It must not be confused with `l2_spectra` (`cnmf.py:882`, what clustering operates on) or
with the unnormalized `merged_spectra`.

### 3.2 `transform: training_fitted_and_leakage_audited`

Every quantity below is estimated on **training donors only** and then applied unchanged to
held-out cells.

- **Gene universe `G`** — the high-variance gene panel selected by cNMF's Fano-factor method,
  computed on training donors only. Frozen for the fold.
- **Per-gene scale `s_g`** — the standard deviation with **`ddof=1`** of the raw counts of gene
  `g`, over training cells only, computed on the `G`-subset matrix. This mirrors upstream
  `get_norm_counts` (`cnmf.py:536-543`), which divides by the per-gene std with
  `zero_center=False` — no centring, no per-cell library normalisation.
- **Transform** — `X[c,g] = rawcount[c,g] / s_g` for every cell `c`, training or held-out.

**`ddof=1` is measured, not assumed.** The harness's `s_g` must *equal* what cNMF used internally,
or the transform used for scoring would sit on a different scale than the one the dictionary was
learned from. Verified at S0-03 against the reference `norm_counts` already shown bitwise identical
in `SOURCE_AUDIT.md` §1.5.2 (simulated dataset, 2500 cells × 1000 HVGs): dividing the HVG-subset
raw counts by `std(axis=0, ddof=1)` reproduces it to a relative Frobenius error of **1.7e-14**,
while `ddof=0` gives **2.0e-4** — four orders of magnitude outside D004's 1e-5 and unambiguously
wrong.

*Implementation hazard, characterised rather than merely flagged:* upstream's branch at
`cnmf.py:537` tests `sp.issparse(tpm.X)` but scales `norm_counts`, so when those two objects differ
in sparsity the branch chosen does not describe the object being scaled. Measured consequence for
`s_g`: **none.** Both branches divide by the same quantity — `sc.pp.scale(zero_center=False)`
(scanpy 1.11.5) agrees with a manual `ddof=1` division to 6.4e-16 on both dense and CSR input, and
disagrees with `ddof=0` by 2.5e-3. The mismatch is a latent code smell, not a numerical fork, and
the harness's independently computed `s_g` therefore agrees with upstream on either path. Recorded
so that a future session does not re-derive this from the source and reach the opposite conclusion.
See `SOURCE_AUDIT.md` §1.2.

**"Leakage audited"** means the claim is tested, not asserted: P0-05 must demonstrate that
perturbing held-out values leaves `G`, `s_g`, the dictionary and the inference-panel usages
bitwise unchanged (`IMPLEMENTATION_PROMPT.md:192`).

### 3.3 `nonnegative_least_squares_frozen_dictionary`

Let `V = median_spectra`, a `K × |G|` nonnegative matrix, frozen — fitted on training cells and
**never updated on test data** (`test_spectra_refit: forbidden`).

For each held-out cell `c`, usages come from the **inference panel only**:

    U_test[c,:] = argmin_{u >= 0}  || X[c, G_inf]  -  u · V[:, G_inf] ||²

Notes that matter:

- Subsetting `V` to a panel breaks its row-sum-to-1 property. This is harmless: `U` absorbs the
  magnitude, and no step downstream assumes the subset sums to 1.
- The problem is **convex** in `u` with `V` fixed, so the optimum is unique and initialisation
  cannot affect the result. This is the same property measured in `SOURCE_AUDIT.md` §1.5.1, where
  the unseeded upstream refit nevertheless produced bitwise-identical artifacts across 10 repeats.
- The harness must give cNMF **training cells only** in its `norm_counts`/`tpm` inputs, because
  `consensus()` internally refits usages against every cell present in the files it reads
  (`cnmf.py:961-975`). With training-only inputs, `test_spectra_refit: forbidden` holds by
  construction rather than by enforcement.

### 3.4 `training_scale_squared_prediction_error`

The primary loss (`ablation_plan.yaml: primary_loss`). Scored on the **validation panel only** —
genes withheld from the usage estimation of that same cell.

    prediction[c, G_val] = U_test[c,:] · V[:, G_val]

    L[c] = sum_{g in G_val}  ( X[c,g] - prediction[c,g] )²

`X` here is the training-scale transform of §3.2, so the loss is in training scale — hence the
name. Gene weights are implicitly the `1/s_g` of the transform, and are **identical across every
variant being compared** within a fold (`IMPLEMENTATION_PROMPT.md:190`).

Reported alongside, not instead: the count-unit back-transform, obtained by multiplying residuals
by `s_g` before squaring. Two numbers, two named metrics (§5.2), never silently interchanged.

This is a **squared loss**. It must never be labelled a likelihood, and native losses of different
methods must never be compared as though they were this metric.

**Null predictor.** Required, and must be handicapped identically: the training mean profile over
`G`, treated as a rank-1 dictionary, with its amplitude `u` fit by the **same NNLS on `G_inf`
only** (`IMPLEMENTATION_PROMPT.md:190`). A null predictor that saw the validation panel, or that
used a fixed amplitude, would not be a fair floor.

The evaluated gene universe, the loss weights and the null predictor are frozen within a fold.

**Scope across arms (D016, v1.1).** The training-scale loss is primary wherever
the compared arms share `s_g` — within one arm across ranks (feature A), and
across C arms (identical factor banks, identical cells). Where the arms cannot
share `s_g` — feature B, whose sampling rule changes which cells reach
`cnmf.prepare` and hence the scale itself (measured drift median 1.04, max
1.24) — the **count-unit back-transform is the primary endpoint** and the
training-scale number is reported beside it, never compared across arms. This
resolves the `ablation_plan.yaml:63` vs `contracts/B.md` conflict on the side
of the units the arms share; `contracts/B.md` needs no change.

### 3.5 `equal_donor_mean`

The primary aggregation (`ablation_plan.yaml: primary_aggregation`).

    per_donor[d]  = mean over that donor's scored cells of L[c]
    equal_donor_mean = unweighted mean over donors of per_donor[d]

Average **within donor first, then unweighted across donors**, so a donor contributing many cells
does not dominate. The donor is the independent unit
(`validation.group_by: donor_id`, `keep_repeated_measurements_together: true`); cells are not
independent samples and must not be treated as such in any interval or test.

Donors with zero scored cells are excluded and counted in `n_failed_units`; they are not entered
as zeros.

---

## 4. `fixed_gene_panels`

The within-test-donor split (`ablation_plan.yaml: within_test_donor_split`).

### 4.1 Construction

The gene universe `G` is partitioned into two disjoint panels:

    G = G_inf  ⊔  G_val,        |G_inf| = round( inference_gene_fraction · |G| )

`inference_gene_fraction` comes from the run configuration (`0.7` in `smoke.yaml`). Panels are
drawn from a **panel seed that is independent of the sampling seed and of the optimizer seed**, so
that panel variation and optimisation variation can be separated. Each realized panel is
identified by `mask_id`.

**Panels are identical across all candidate ranks and all A/B/C configurations within a
comparison** (`IMPLEMENTATION_PROMPT.md:177`). Two arms that differ in their panels are not
comparable, and the harness must refuse such a comparison rather than report it.

Training donors keep **all** eligible genes. Only held-out donors have a panel withheld, and only
from their usage estimation (§3.3) — their validation-panel values are still used for scoring.

### 4.2 Zeros

`observed_zero_is_not_missing: true`. An observed zero is data. Zeros stay in `G_inf` for
estimation and in `G_val` for scoring. Panels must cover zeros as well as nonzeros
(`IMPLEMENTATION_PROMPT.md:177`); a panel construction that conditioned on expression level would
be data-dependent and is forbidden.

### 4.3 Insufficient-information rule

A held-out cell whose total count over `G_inf` is zero makes the NNLS degenerate — there is no
information to estimate its usages from.

**Rule:** exclude that cell from scoring, count it in `n_failed_units`, and report the per-fold
failure rate. **Never** substitute a different panel for it: choosing a panel because the first one
failed on that cell is test-informed panel selection (`IMPLEMENTATION_PROMPT.md:177`).

Upstream raises a hard exception on zero-HVG-count cells (`cnmf.py:550-554`). The harness's
projection code must **degrade gracefully** — record the failure and continue — rather than
inherit that crash and lose the rest of the fold.

Panel sizes and dictionary identifiability on the inference panel are recorded per fold.

### 4.4 Nested donor folds and inner-fold identity

Feature A selects rank on **inner** donor folds nested inside each outer
training fold (P0-05): inner-training donors fit candidate dictionaries, inner-
validation donors score them via the §3.3/§3.4 machinery with a panel drawn over
the inner `G`. The inner fit selects its own `G` and `s_g` from inner-training
cells only — reusing the outer fold's would leak inner-validation donors into
rank selection one level down. Inner-fold rows carry an `inner_split_id` in
their `experiment_id` (following the `variant` precedent, D025); two inner
folds of one outer fold at one rank must never collide on identity. The inner
loop runs only when feature A is on; the A-OFF baseline never reads an inner
validation fold (its selector inputs pre-exist on disk after the rank sweep,
§1.1).

---

## 5. Metric vocabulary

### 5.1 Row semantics

`RESULTS.tsv` is tidy: one row per (experiment, unit, metric). Controlled strings only — a metric
name not listed in §5.2 may not be written. Every row carries `metric_definition_version` and
`direction` (`lower_is_better` or `higher_is_better`).

The `independent_unit_type` for primary endpoints is `donor`, per §3.5.

### 5.2 Vocabulary (`metric_definition_version: 2`)

| `metric` | `direction` | Definition |
|---|---|---|
| `heldout_squared_prediction_error_v1` | lower | §3.4, training scale, aggregated per §3.5 |
| `heldout_squared_prediction_error_counts_v1` | lower | §3.4 count-unit back-transform |
| `null_squared_prediction_error_v1` | lower | §3.4 null predictor, inference-panel amplitude only |
| `program_recovery_cosine_v1` | higher | `Σ(matched cosine) / max(K_true, K_inferred)`; one-to-one maximum-weight matching on **full loading vectors in common gene units** via `scipy.optimize.linear_sum_assignment`, with dummy factors absorbing unmatched components. Record matched, missing, extra and ambiguous counts. |
| `program_precision_v1` | higher | Threshold **0.90**, calibrated at P1-01 (see below). A true program counts as recovered when its matched cosine clears the threshold; precision divides by `K_fitted`. |
| `program_recall_v1` | higher | Same threshold **0.90**; recall divides by `K_true`. |
| `ambiguous` | — | Count of true programs whose top-2 cosine gap falls below **0.20**, calibrated at P1-01 (see below). A diagnostic safeguard, not a primary endpoint. |
| `usage_error_v1` | lower | **Reuses the alignment computed from loadings** for `program_recovery_cosine_v1`. Re-deriving an alignment from usages would flatter the method. Missing and extra components are retained as error terms in a union representation, not dropped. |
| `wall_seconds_v1` | lower | Elapsed wall time of the scored unit of work |
| `cpu_seconds_v1` | lower | CPU time; `memory_scope` in `EXPERIMENTS.tsv` records what was measured |
| `peak_memory_mb_v1` | lower | Peak RSS; scope as above |
| `failed_fits_v1` | lower | Count of fits that did not complete; always emitted, including as 0 |
| `program_recovery_jaccard_v1` | higher | Gene-set sibling of the cosine metric (v1.2, second cycle): Hungarian maximum-weight one-to-one matching on **Jaccard similarities between gene sets**, with dummy factors absorbing unmatched components; score `Σ(matched Jaccard) / max(K_true, K_inferred)`. True side: simulator marker sets; fitted side: top genes per program (see §5.5). For whole-workflow comparator rows only — never a cNMF-vs-cNMF endpoint. |

**Threshold calibration, P1-01 (D033).** Both constants were set on DEVELOPMENT
controls only (`p04-dev-000m`, configuration 000, both outer folds at
`K_true = 7`), before any A-ON row exists; full distributions in
`registry/p1-01_threshold_calibration.tsv`. Recovery threshold **0.90**: the
observed separation band between the matched null (max 0.833 over both folds)
and genuinely recovered programs (min 0.974) is [0.84, 0.97], and 0.90 is its
midpoint; below it sit the null (≤0.833), the noise-replaced control
(0.72–0.75) and the deleted-program dummy (0.0). Ambiguous threshold **0.20**:
top-2 gaps at `K_true` are all ≥0.354 in both folds, while off-rank fits show
gaps down to 0.0003; 0.20 flags the latter with zero false alarms at `K_true`.
Neither value was adjusted on any outer-test result or to favour a later
comparison; both are frozen with this version.

### 5.4 Controlled vocabularies (D009, solemnised here)

The row schemas' controlled strings, enforced in `cnmfbench/records.py` since
the skeleton session and frozen here as part of the single v1.1 amendment
rather than a second versioning: `status ∈ {ok, ok_provisional, fit_failed,
scoring_failed}` (blank = true null, `NOT_COMPUTED` = could not be produced);
`evaluation_scope` names the unit the row aggregates over and is a required
filter on any aggregation; `arm ∈ {full_training_pool, matched_budget,
upstream_full_data, genenmf_native}`. No rule changes — this section writes
down what the writer already enforces.

### 5.5 Gene-set reduction and comparator hyperparameters (v1.2, frozen pre-results)

The Jaccard metric needs gene *sets* on both sides, and the reductions below
are frozen by published precedent — not tuned, since no comparator row exists
yet and the constants below were written before any was produced:

- **cNMF side: top 50 genes** per consensus program by spectra weight (Gavish et
  al. 2023 precedent). No specificity weighting, no weight-explained cutoff.
- **GeneNMF side: native meta-program gene lists** (`metaprograms.genes`) from
  the native `multiNMF → getMetaPrograms` workflow.
- **`nMP = 10`** (GeneNMF native default; the BCC paper's target with no stated
  rationale — recorded as unjustified rather than back-justified).
- **HVG input: native default `nfeatures = 2000`**; ranks `k = 4..10` (the
  DEVELOPMENT candidate grid, shared for comparability); seed 123 (GeneNMF
  default policy); Seurat LogNormalize `data` slot.
- GeneNMF-side truth comparison needs no usage projection: simulator marker
  sets are gene sets natively, so truth meets the comparator in its own units.
  Any NNLS-projected usage score would be labeled adapter-derived (§204 of the
  brief) and is not built in this cycle.

Cost metrics are reported for every configuration, always, so that a gain is never assessed
without its price (`cost_cap` lives in the feature contracts).

### 5.3 Fixed-rank rows: `selected_rank` is null **by design**

`RESULTS.tsv` carries both `candidate_rank` and `selected_rank`. For an arm that does not select a
rank — every A-OFF configuration in `fixed_rank_configurations`, and all P0 work (§2) — the row
records `candidate_rank` and leaves `selected_rank` **null**, with `status` indicating success.

A later reader must interpret a null `selected_rank` on a successful row as *"this arm did not
select a rank"*, **not** as *"the selector failed"*. The failure case is distinguishable: it also
has a null `selected_rank`, but its `status` records the failure and `n_failed_units` is nonzero
(§1.4).

A complete fixed-rank curve is a set of such rows, one per grid value.

---

## 6. Data contract

Normative statement. **P0-02 implements validation of this contract and must not redefine it**;
the simulator (P0-03) implements against it. Recorded here because the simulator is built before
the schema layer (decision D006).

### 6.1 Orientation and dtype

- Count matrices are **cells × genes**. This matches cNMF's `AnnData` convention (`obs` = cells,
  `var` = genes) and is checked, not assumed.
- Raw counts are stored as integers; transformed matrices as `float64`. Upstream casts to
  `float64` before factorization (`cnmf.py:534`).
- Cell identifiers are unique strings in `obs.index`; gene identifiers are unique strings in
  `var.index`. Neither may be positional integers.

### 6.2 Units at each stage

Named explicitly, because three different normalizations circulate and conflating them is the
single easiest way to invalidate a result (`SOURCE_AUDIT.md` §1.2):

| Stage | Units |
|---|---|
| Simulator output | raw integer counts |
| `X` (§3.2) | raw counts divided by training per-gene std; **no per-cell normalisation** |
| `V = median_spectra` | rows sum to 1 over the full `G` |
| `prediction` (§3.4) | training scale, same as `X` |

### 6.3 Donor labels and ground truth

- The donor label column is `obs['donor_id']`, a string. It is the independent unit everywhere
  (§3.5) and the grouping key for every split.
- Ground truth is stored **alongside** the counts, never inside them: true spectra as a
  `K_true × n_genes` matrix in gene order matching `var.index`, true usages as
  `n_cells × K_true` in cell order matching `obs.index`. Both are written even when unused, so a
  later metric can be computed without regenerating data.
- Ground truth is never an input to any selector, transform or fit (§1.5).

### 6.4 Data tiers

Three tiers, per `IMPLEMENTATION_PROMPT.md:141`:

| Tier | Purpose | May inform design? |
|---|---|---|
| `SMOKE` | Does the code run? | Yes — but can never promote a feature (`smoke_can_promote_feature: false`) |
| `DEVELOPMENT` | Calibration, pilot variability, constant-setting (`delta`, thresholds, margins) | Yes, and only this tier may |
| `SEALED_CONFIRMATION` | Confirmation after freezing | **No.** Evaluated only after the configuration is frozen |

**Sealed manifest policy, frozen now while nothing is tempted to peek:** the sealed tier's
generating seeds and manifests are written at creation and not read during development. Once a
sealed set has been used to redesign the method, it is marked **consumed** and a new independent
set is required (`IMPLEMENTATION_PROMPT.md:268`). The reusable regression suite becomes
development data through repeated use and may never be reported as confirmation.

### 6.5 The simulator's observation model is not a deferred feature

`smoke.yaml` sets `observation_model: poisson`. This is the **simulator's generative model** — how
synthetic counts are drawn — and it is unconstrained by the brief's deferred "NB/Poisson
backends", which concern the **factorization loss** inside cNMF.

The factorization loss stays `frobenius` (`smoke.yaml: factorization.loss`), which is upstream's
default and the only loss this cycle uses. Implementing a Poisson or negative-binomial *solver*
remains deferred and must not be introduced implicitly.

### 6.6 `dataset_manifest_hash` inputs

Hashed (per §7) over the canonical JSON of: scenario id, tier, all generative parameters (donors,
cells per donor, genes, true programs, observation model and its parameters), the simulation seed,
`simulation_replicate`, and this protocol's version. Two datasets with the same manifest hash must
be bitwise identical; two that differ in any of the above must not collide.

### 6.7 Feasibility pre-registrations carry an instrument-failure branch (D012)

Every feasibility pre-registration written under this protocol must include,
alongside benchmark-failure responses, the branch the v1 menu lacked: "the
criterion was mis-specified — record the verdict unchanged, argue the defect
from the run's own data, pre-register a replacement, and test it on a fresh
seed it did not motivate." A criterion rewritten by whoever just watched it
fail carries no evidential weight; a re-scored old run is not a result.

---

## 7. Hash convention

`hash_convention_version: 1`. One rule per kind of thing, so that a hash is reproducible without
reading the code that produced it.

| Kind | Rule |
|---|---|
| **Parameter-like** (`protocol_hash`, `contract_hash`, `preprocessing_hash`, `dataset_manifest_hash`, `environment_hash`) | `sha256` over **canonical JSON**: keys sorted lexicographically, no insignificant whitespace (`separators=(',',':')`), UTF-8, `ensure_ascii=False`, floats in `repr` form |
| **Artifact** (`factor_bank_hash`, file-level integrity) | `sha256` over the **file bytes**, unmodified |
| **Cell set** (`discovery_cells_hash`) | `sha256` over the newline-joined, **lexicographically sorted** list of `cell_id`, UTF-8, trailing newline included |
| **This file** (`protocol.sha256`) | `sha256` over the file bytes, as an artifact hash |

Hashes are recorded as lowercase hex, full length, never truncated. Any change to these rules
increments `hash_convention_version` and invalidates comparison of hashes across the boundary.

---

## 8. Out of scope for this file

Deliberately absent, so their absence is not read as an oversight:

- **All five numerical margins** in `ablation_plan.yaml` — `primary_minimum_worthwhile_gain`, the
  three harm margins, and `cost_cap`. They belong in `contracts/{A,B,C}.md`, set from development
  pilot variability, per `FEATURE_CONTRACT_TEMPLATE.md`. `null_margin_policy:
  refuse_scientific_adoption_decision` already enforces that a numerical gate refuses to run while
  they are null.
- **Feature hypotheses** for A, B and C — contracts.
- **Adoption verdicts** (KEEP / CONDITIONAL / DROP / INCONCLUSIVE) and software statuses
  (UNTESTED / PASS / FAIL / BLOCKED) — gates, recorded as two separate decisions.
- **Deferred features** — NB/Poisson factorization backends, Bayesian uncertainty, GPU execution,
  donor-aware HVG selection. None is implemented implicitly (§6.5).

---

## 9. What "frozen" means

**Frozen:** every rule in §§1, 3, 4, 5, 6, 7. These may not be changed to accommodate a result.

**Not yet set, by design:** none at the protocol level — v1.1 sets `delta`
(§2) and both §5.2 thresholds. Numerical decision margins live in
`contracts/{A,B,C}.md`, not here (§8).

**Amendment rules:**

1. Any change to a frozen rule creates a **new protocol version** with a new file hash written into
   `ablation_plan.yaml`, and a `DECISIONS.md` entry recording what changed and why.
2. A new protocol version **invalidates confirmation** obtained under the previous one. Results
   already recorded keep the `protocol_hash` they were produced under; they are not retro-labelled.
3. Changes justified by **outer-test or confirmation results are forbidden**, not merely
   discouraged. Changes justified by inner-development evidence are permitted as a new version
   requiring fresh confirmation (`IMPLEMENTATION_PROMPT.md:215`).
4. No dataset or code change may silently rewrite an existing benchmark decision
   (`IMPLEMENTATION_PROMPT.md:268`).

---

## References

- `docs/IMPLEMENTATION_PROMPT.md` — §P0.4 (:177, :188, :190, :192), §P0.5 (:196, :198), §P1 (:215), §sealed data (:268)
- `Stepwise_Guide.md:85` — upstream's documented rank-selection practice
- `src/cnmf/cnmf.py` — `get_norm_counts` scaling (:536-543), zero-HVG exception (:550-554), `l2_spectra` (:882), KMeans `random_state=1` (:908), `median_spectra` (:913-916), final refit (:961-975), `k_selection_plot` (:1119-1158)
- `docs/planning/SOURCE_AUDIT.md` §1.2 (dataflow), §1.5 (determinism and tolerance)
- `docs/planning/DECISIONS.md` — D004 (tolerance, provisional), D005 (upstream test failure), D006 (P0-03 before P0-02)
