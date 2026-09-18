"""The transform, the frozen-dictionary projection, and the loss (PROTOCOL §3.2-§3.5, §4.3).

Four things in here produce a plausible wrong number rather than an error if they are got
wrong, so each is stated where it is implemented:

1. **The null predictor's units.** The training mean profile must be the mean of the
   *scaled* matrix `X = raw/s_g`, not of raw counts. Measured on SMOKE: using the raw
   mean inflates the null floor roughly 4x (97.1 vs 24.4), with no crash, making the
   model look four times better than it is.
2. **Gene indexing by label.** The dictionary's columns are gene *names*. Indexing by
   position after any `set()` or `sorted()` permutes `V` against `X`.
3. **Zero-variance genes raise here.** `diagnostics.training_gene_std` floors them to
   1.0, which matches cNMF's *sparse* branch; the dense branch divides by zero and only
   prints a warning. Flooring would make the harness's `X` silently disagree with the
   dictionary's own training space on exactly the pathological gene, so this module
   refuses instead. (Measured on SMOKE: min `s_g` is 0.86, zero such genes — the guard is
   for when the training cell count drops or the gene count rises.)
4. **§4.3 exclusions are not failures to paper over.** A held-out cell with zero total
   count over `G_inf` has no information to estimate usages from. Exclude it, count it,
   never substitute a different panel — choosing a panel because the first failed on that
   cell is test-informed panel selection.
"""
import numpy as np
from scipy.optimize import nnls

from .contract import ContractViolation

__all__ = [
    "training_gene_scale",
    "to_training_scale",
    "nnls_usages",
    "scoreable_mask",
    "null_dictionary",
    "squared_prediction_error",
    "count_unit_error",
    "equal_donor_mean",
    "DonorAggregate",
]


def training_gene_scale(train_counts_on_g):
    """`s_g` = std of raw training counts, `ddof=1`, on the `G`-subset (§3.2).

    `ddof=1` is measured, not assumed: it reproduces upstream's `norm_counts` to a
    relative Frobenius error of 1.7e-14 against 2.0e-4 for `ddof=0` (PROTOCOL §3.2).

    Raises rather than flooring a zero-variance gene — see the module docstring.
    """
    x = np.asarray(train_counts_on_g, dtype=np.float64)
    if x.ndim != 2 or x.shape[0] < 2:
        raise ValueError(f"need at least 2 training cells, got shape {x.shape}")
    s = x.std(axis=0, ddof=1)
    bad = np.flatnonzero(s == 0)
    if bad.size:
        raise ContractViolation(
            f"{bad.size} gene(s) have zero variance across training cells "
            f"(first at column {bad[0]}). cNMF's dense branch divides by this and emits "
            "inf/NaN with only a printed warning; flooring it to 1.0 would put the "
            "harness's X in different units from the dictionary on exactly that gene."
        )
    return s


def to_training_scale(counts_on_g, s_g):
    """`X[c,g] = rawcount[c,g] / s_g` — for every cell, training or held out (§3.2).

    No per-cell library normalisation. §3.1 forbids it as leakage: a held-out cell's
    total over all genes includes its own validation panel.
    """
    return np.asarray(counts_on_g, dtype=np.float64) / np.asarray(s_g, dtype=np.float64)[None, :]


def nnls_usages(x_inference, v_inference):
    """`U[c,:] = argmin_{u>=0} ‖X[c,G_inf] − u·V[:,G_inf]‖²` (§3.3).

    Solved exactly, per cell, with `scipy.optimize.nnls`. §3.3 states the problem is
    convex with `V` fixed, so the optimum is unique and this *is* the defined answer;
    cNMF's own `refit_usage` uses coordinate descent to `tol=1e-4`, which only
    approximates it and would make the P0-05 leakage test non-bitwise.

    `v_inference` is `K × |G_inf|`, so the least-squares design matrix is its transpose.

    Un-fenced at D021: `test_leakage.py` shows perturbing a held-out cell's
    validation-panel counts leaves its inference-panel usages bitwise unchanged, closing
    this function's `hardening_requires`.
    """
    x = np.asarray(x_inference, dtype=np.float64)
    v = np.asarray(v_inference, dtype=np.float64)
    if x.shape[1] != v.shape[1]:
        raise ValueError(f"gene axis mismatch: X has {x.shape[1]}, V has {v.shape[1]}")
    a = np.ascontiguousarray(v.T)
    return np.vstack([nnls(a, row)[0] for row in x])


def scoreable_mask(raw_counts_on_inference):
    """True for held-out cells with any signal on `G_inf` (§4.3).

    A cell with zero total there makes the NNLS degenerate — `u = 0` is the exact
    optimum, and scoring it would enter the null prediction as though it were a real
    result. Exclude and count it instead.
    """
    return np.asarray(raw_counts_on_inference).sum(axis=1) > 0


def null_dictionary(x_train):
    """The §3.4 null: the training mean profile over `G`, as a `1 × |G|` dictionary.

    **`x_train` must already be in training scale.** Passing raw counts inflates the
    floor by roughly 4x on SMOKE and nothing warns. Its amplitude is fit by the same
    `nnls_usages` on `G_inf` only, so §3.4's "handicapped identically" holds by
    construction rather than by review.
    """
    x = np.asarray(x_train, dtype=np.float64)
    profile = x.mean(axis=0, keepdims=True)
    if not np.all(profile >= 0):
        raise ContractViolation("null profile has negative entries")
    if profile.sum() == 0:
        raise ContractViolation("null profile is all zero")
    return profile


def squared_prediction_error(x_validation, usages, v_validation):
    """Per-cell `L[c] = Σ_{g∈G_val} (X[c,g] − U[c,:]·V[:,g])²` (§3.4), training scale."""
    residual = np.asarray(x_validation, dtype=np.float64) - usages @ np.asarray(
        v_validation, dtype=np.float64
    )
    return (residual**2).sum(axis=1)


def count_unit_error(x_validation, usages, v_validation, s_g_validation):
    """The §3.4 count-unit back-transform: multiply residuals by `s_g` before squaring.

    Reported *alongside* the training-scale metric, never instead of it — two numbers,
    two named metrics. Note it is **less** comparable across folds than the training-scale
    metric, because it weights by `s_g²` and both `G` and `s_g` are refitted per fold.
    """
    residual = np.asarray(x_validation, dtype=np.float64) - usages @ np.asarray(
        v_validation, dtype=np.float64
    )
    return ((residual * np.asarray(s_g_validation, dtype=np.float64)[None, :]) ** 2).sum(axis=1)


class DonorAggregate:
    """Result of §3.5 aggregation, carrying the counts the schema needs.

    `per_donor` is the payload: `RESULTS.tsv` has an `independent_unit_id` column and
    §5.1 wants one row per (experiment, unit, metric), so the per-donor values are
    written and the aggregate derived — not the other way round. Measured on SMOKE,
    per-donor error ranges 99-250 within one fold and tracks sequencing depth, so an
    aggregate alone discards the structure the schema exists to record.
    """

    __slots__ = ("value", "per_donor", "n_eligible_donors", "n_failed_donors")

    def __init__(self, value, per_donor, n_eligible_donors, n_failed_donors):
        self.value = value
        self.per_donor = per_donor
        self.n_eligible_donors = n_eligible_donors
        self.n_failed_donors = n_failed_donors


def equal_donor_mean(per_cell_loss, donor_ids):
    """Average within donor first, then unweighted across donors (§3.5).

    Un-fenced at P0-04 (D017) once its own corruption/invariance battery was written —
    `test_splits_and_scoring.py`, seven tests: invariance to cell order, to donor
    relabelling, to replicating a donor's cells, and positive homogeneity; plus the
    penalty that damaging one of n donors moves the aggregate by exactly `delta/n`, and
    the refusals. The recovery metrics' battery does not cover any of these: the property
    this function exists for — a donor's weight is independent of its cell count — is
    invisible to any test of the metric being aggregated.

    Donors are the independent unit; cells within a donor are not independent samples.
    Donors with zero scored cells are **excluded and counted**, never entered as zeros —
    a zero would be read as a perfect prediction.
    """
    loss = np.asarray(per_cell_loss, dtype=np.float64)
    donors = np.asarray([str(d) for d in donor_ids])
    if loss.shape[0] != donors.shape[0]:
        raise ValueError(f"{loss.shape[0]} losses for {donors.shape[0]} donor labels")

    per_donor, failed = {}, 0
    for d in sorted(set(donors.tolist())):
        sel = loss[donors == d]
        if sel.size == 0:
            failed += 1
            continue
        per_donor[d] = float(sel.mean())

    if not per_donor:
        raise ContractViolation("no donor has a scored cell; the fold produced no value")
    return DonorAggregate(
        value=float(np.mean(list(per_donor.values()))),
        per_donor=per_donor,
        n_eligible_donors=len(per_donor),
        n_failed_donors=failed,
    )
