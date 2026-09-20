"""Program recovery: did the fit find the right programs, whatever rank it used?

This is the metric that carries the scientific question, and it has one failure mode that
dominates every other: **comparing spectra that live in different unit systems**. The truth
is generated in count space; cNMF's `median_spectra` lives in the engine's scaled space,
where every gene has been divided by its training standard deviation `s_g` (PROTOCOL §3.2,
`cnmf.py:542`). Cosine is invariant to scaling a *vector*, but not to scaling each
*coordinate* by a different `s_g` — that is a shear, and it rotates the vectors.

Measured on the skeleton's own SMOKE run, with `K_true = 3`:

| | K=2 | **K=3 = K_true** | K=4 |
|---|---|---|---|
| **Aligned** — fitted | 0.660 | **0.988** | 0.739 |
| **Aligned** — matched null | 0.574 | 0.850 | 0.637 |
| **Unaligned** — fitted | 0.449 | 0.703 | 0.528 |
| **Unaligned** — matched null | 0.558 | 0.819 | 0.614 |

Unaligned, the null beats the fit at *every* rank in *both* folds: the metric reports that
cNMF recovers programs worse than a trivial average of the truth. Aligned, the fit wins
everywhere and peaks exactly at `K_true`. Both routes to common units agree (0.9881 pushing
truth into scaled space, 0.9888 pulling the dictionary into count space), so the choice
between them is free. **Failing to choose is what breaks the metric.**

So units are not a convention here, they are the result. `Spectra` carries its space as data
and `recovery_cosine` refuses a mismatch rather than scoring it — an unaligned comparison
raises `UnitMismatch` instead of silently returning a number that inverts the finding.
"""
import dataclasses

import numpy as np
from scipy.optimize import linear_sum_assignment

__all__ = [
    "SPACES",
    "UnitMismatch",
    "Spectra",
    "Alignment",
    "recovery_cosine",
    "matched_null_spectra",
    "usage_error",
    "ThresholdNotCalibrated",
    "program_precision_recall",
    "top2_cosine_gaps",
    "ambiguous_program_count",
    "top_genes",
    "recovery_jaccard",
]


class ThresholdNotCalibrated(RuntimeError):
    """A metric whose constant PROTOCOL §5.2 leaves null was asked for a number.

    The refusal is the feature. The code exists and is tested; what does not exist is a
    threshold, and inventing one here — having already seen this data — is exactly what the
    null-until-calibrated policy prevents. Same pattern as the rank selector while `delta`
    is null.
    """


SPACES = ("count", "scaled")


class UnitMismatch(ValueError):
    """Two spectra were about to be compared across different unit systems or gene axes."""


def _rows_unit_norm(matrix):
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    # A zero row has no direction. It scores 0 against everything, which is the honest
    # answer for an empty program, so it is normalised to zero rather than to noise.
    safe = np.where(norms > 0, norms, 1.0)
    return matrix / safe


@dataclasses.dataclass(frozen=True)
class Spectra:
    """A K x |genes| nonnegative loading matrix that knows which unit system it is in.

    `space` is the whole point of this class. It is not documentation; `recovery_cosine`
    reads it and refuses on a mismatch.
    """

    matrix: np.ndarray
    space: str
    gene_labels: tuple

    def __post_init__(self):
        if self.space not in SPACES:
            raise ValueError(f"space must be one of {SPACES}, got {self.space!r}")
        if self.matrix.ndim != 2:
            raise ValueError(f"matrix must be 2-D, got shape {self.matrix.shape}")
        if self.matrix.shape[1] != len(self.gene_labels):
            raise ValueError(
                f"matrix has {self.matrix.shape[1]} columns but {len(self.gene_labels)} "
                "gene labels were given"
            )
        if np.any(self.matrix < 0):
            raise ValueError("spectra must be nonnegative")

    @property
    def n_programs(self):
        return self.matrix.shape[0]

    def to_scaled(self, s_g):
        """Divide each gene by its training standard deviation, matching what cNMF's engine
        saw. `s_g` must be indexed by this object's own `gene_labels`."""
        if self.space == "scaled":
            return self
        s_g = np.asarray(s_g, dtype=float)
        if s_g.shape != (len(self.gene_labels),):
            raise UnitMismatch(
                f"s_g has shape {s_g.shape}, expected ({len(self.gene_labels)},) to match "
                "this object's gene axis"
            )
        if np.any(s_g <= 0):
            raise UnitMismatch("s_g contains non-positive entries; the transform is undefined")
        return dataclasses.replace(self, matrix=self.matrix / s_g, space="scaled")

    def to_count(self, s_g):
        """The inverse route. Kept because the two routes agreeing is the evidence that the
        alignment is right, and a test compares them."""
        if self.space == "count":
            return self
        s_g = np.asarray(s_g, dtype=float)
        if s_g.shape != (len(self.gene_labels),):
            raise UnitMismatch(
                f"s_g has shape {s_g.shape}, expected ({len(self.gene_labels)},)"
            )
        if np.any(s_g <= 0):
            raise UnitMismatch("s_g contains non-positive entries; the transform is undefined")
        return dataclasses.replace(self, matrix=self.matrix * s_g, space="count")

    def subset_genes(self, gene_labels):
        """Restrict to `gene_labels`, in that order. Raises if any is absent, rather than
        silently intersecting — a shrunk gene axis would change the metric without saying so.
        """
        position = {g: i for i, g in enumerate(self.gene_labels)}
        missing = [g for g in gene_labels if g not in position]
        if missing:
            raise UnitMismatch(
                f"{len(missing)} requested gene(s) are absent from this spectra's axis, "
                f"first {missing[0]!r}"
            )
        idx = [position[g] for g in gene_labels]
        return dataclasses.replace(
            self, matrix=self.matrix[:, idx], gene_labels=tuple(gene_labels)
        )


@dataclasses.dataclass(frozen=True)
class Alignment:
    """Which fitted program was matched to which true program, and at what cosine.

    Held as an object, not recomputed, because `usage_error_v1` must reuse *this* matching.
    Re-deriving a matching from usages would pick the permutation that makes usages agree
    best, which measures the search rather than the fit.
    """

    true_to_fitted: tuple  # length K_true; fitted index, or None if matched to a dummy
    cosines: tuple  # length K_true; 0.0 where matched to a dummy
    n_true: int
    n_fitted: int

    @property
    def unmatched_true(self):
        return tuple(i for i, j in enumerate(self.true_to_fitted) if j is None)

    @property
    def unmatched_fitted(self):
        used = {j for j in self.true_to_fitted if j is not None}
        return tuple(j for j in range(self.n_fitted) if j not in used)


def recovery_cosine(truth, fitted):
    """One-to-one maximum-weight matching between true and fitted programs.

    Both arguments are `Spectra`. They must agree in `space` and in `gene_labels`; otherwise
    this raises rather than returning a number, because the number it would return is known
    to invert the finding (see the module docstring).

    Dummy factors absorb the unmatched side, and the score divides by `max(K_true, K_fitted)`
    so that both missing a true program and inventing a spurious one are penalised. A fit
    that duplicates a good factor cannot score above a fit that found each program once.
    """
    if not isinstance(truth, Spectra) or not isinstance(fitted, Spectra):
        raise TypeError("recovery_cosine takes Spectra objects, so that units travel with the data")
    if truth.space != fitted.space:
        raise UnitMismatch(
            f"truth is in {truth.space!r} space and the fit is in {fitted.space!r} space. "
            "Cosine is invariant to scaling a vector but not to scaling each gene by a "
            "different s_g, which is a shear. Measured, the unaligned comparison makes a "
            "trivial null beat the fit at every rank. Align explicitly with .to_scaled(s_g) "
            "or .to_count(s_g) before scoring."
        )
    if truth.gene_labels != fitted.gene_labels:
        raise UnitMismatch(
            "truth and fit are on different gene axes; align them with .subset_genes() first"
        )

    t = _rows_unit_norm(np.asarray(truth.matrix, dtype=float))
    f = _rows_unit_norm(np.asarray(fitted.matrix, dtype=float))
    n_true, n_fitted = t.shape[0], f.shape[0]
    cos = t @ f.T  # n_true x n_fitted, all in [0, 1] since both are nonnegative

    # Pad to square with dummy factors scoring 0, so the assignment is always solvable and
    # unmatched programs cost their full weight rather than being dropped.
    size = max(n_true, n_fitted)
    padded = np.zeros((size, size), dtype=float)
    padded[:n_true, :n_fitted] = cos
    rows, cols = linear_sum_assignment(-padded)

    true_to_fitted, cosines = [None] * n_true, [0.0] * n_true
    total = 0.0
    for r, c in zip(rows, cols):
        if r < n_true and c < n_fitted:
            true_to_fitted[r] = int(c)
            cosines[r] = float(cos[r, c])
            total += float(cos[r, c])

    return float(total / size), Alignment(
        true_to_fitted=tuple(true_to_fitted), cosines=tuple(cosines),
        n_true=n_true, n_fitted=n_fitted,
    )


def matched_null_spectra(truth, n_programs):
    """`n_programs` identical copies of the mean true profile.

    Required beside every recovery row, not optional. Measured at SMOKE this null scores
    **0.850** at `K_true` (0.574 at K=2, 0.637 at K=4): a fitted 0.988 is excellent, but
    quoted alone it is indistinguishable from a number whose floor is 0.85, and a weak fit at
    0.87 would read as strong. The null moves with both fold and K, so it is recomputed for
    each rather than carried as a constant.

    It inherits `truth.space`, so a null built from aligned truth is aligned too and the
    comparison cannot drift out of units.
    """
    if n_programs < 1:
        raise ValueError(f"n_programs must be >= 1, got {n_programs}")
    mean_profile = np.asarray(truth.matrix, dtype=float).mean(axis=0)
    return Spectra(
        matrix=np.tile(mean_profile, (n_programs, 1)),
        space=truth.space,
        gene_labels=truth.gene_labels,
    )


def _rows_to_proportions(matrix):
    """Usages are defined up to a per-cell scale, so compare them as proportions. A cell with
    no usage at all keeps a zero row rather than being renormalised into a uniform one."""
    totals = matrix.sum(axis=1, keepdims=True)
    return matrix / np.where(totals > 0, totals, 1.0)


def usage_error(true_usages, fitted_usages, alignment):
    """Mean absolute per-cell usage error, on the matching `recovery_cosine` already found.

    **The alignment is an argument, never re-derived here.** Deriving a second matching from
    the usages would choose whichever permutation makes usages agree best, which measures the
    search rather than the fit — and it could disagree with the permutation the recovery score
    was computed on, so the two metrics would describe different solutions while sharing a row.

    Missing and extra programs are **retained as error**, not dropped. A true program the fit
    never found contributes its whole usage; a fitted program matched to nothing contributes
    its whole usage. Dropping either would reward a fit for omitting what it could not model.
    """
    true_usages = np.asarray(true_usages, dtype=float)
    fitted_usages = np.asarray(fitted_usages, dtype=float)
    if true_usages.shape[0] != fitted_usages.shape[0]:
        raise ValueError(
            f"cell counts differ: {true_usages.shape[0]} true vs {fitted_usages.shape[0]} fitted"
        )
    if true_usages.shape[1] != alignment.n_true or fitted_usages.shape[1] != alignment.n_fitted:
        raise ValueError(
            f"usages have {true_usages.shape[1]}/{fitted_usages.shape[1]} programs but the "
            f"alignment was computed on {alignment.n_true}/{alignment.n_fitted}. Passing an "
            "alignment from a different fit would score one solution's usages against "
            "another's matching."
        )
    if np.any(true_usages < 0) or np.any(fitted_usages < 0):
        raise ValueError("usages must be nonnegative")

    t = _rows_to_proportions(true_usages)
    f = _rows_to_proportions(fitted_usages)

    # Union representation: one column per matched pair, plus one per unmatched program on
    # either side, whose counterpart is implicitly zero.
    columns = []
    for i, j in enumerate(alignment.true_to_fitted):
        columns.append(t[:, i] - f[:, j] if j is not None else t[:, i])
    for j in alignment.unmatched_fitted:
        columns.append(-f[:, j])
    per_cell = np.abs(np.column_stack(columns)).sum(axis=1)
    return float(per_cell.mean()), per_cell


# ------------------------------------------------- metrics that exist in order to refuse

RECOVERY_THRESHOLD = None  # PROTOCOL §5.2 leaves it null; set at P1 on development controls.
AMBIGUITY_THRESHOLD = None  # §5.2 requires the count but defines no threshold. See below.


def program_precision_recall(alignment, threshold=RECOVERY_THRESHOLD):
    """`program_precision_v1` / `program_recall_v1`. **Refuses while the threshold is null.**

    The computation is trivial once a threshold exists — a true program counts as recovered
    when its matched cosine clears `threshold`; precision divides by `K_fitted`, recall by
    `K_true`. What is missing is the threshold, and it is missing on purpose: §5.2 leaves it
    null, and picking a value now, after seeing that fitted programs score ~0.99 and a
    trivial null scores ~0.85, would be choosing the constant against known data.

    The narrowness of that band is the whole difficulty. Any threshold between 0.85 and 0.99
    is defensible in isolation and they give very different answers, so the choice has to be
    made against development *controls* — a null, a duplicated factor, a deleted program —
    not against a fit whose score is already known.

    Passing an explicit `threshold` is allowed so the arithmetic stays testable; it does not
    constitute calibration and nothing may write these metrics to `RESULTS.tsv` until §5.2
    carries a value.
    """
    if threshold is None:
        raise ThresholdNotCalibrated(
            "program_precision_v1 / program_recall_v1 need a cosine threshold that PROTOCOL "
            "§5.2 leaves null by design. Refusing rather than inventing one: measured, a "
            "fitted program scores ~0.99 and a trivial matched null ~0.85, so every value in "
            "between is defensible and they disagree. Calibrate at P1 against development "
            "controls, record it in §5.2, then pass it explicitly."
        )
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must lie in [0, 1], got {threshold}")
    recovered = sum(1 for c in alignment.cosines if c >= threshold)
    return {
        "program_precision_v1": float(recovered / alignment.n_fitted) if alignment.n_fitted else 0.0,
        "program_recall_v1": float(recovered / alignment.n_true) if alignment.n_true else 0.0,
        "threshold": float(threshold),
        "n_recovered": int(recovered),
    }


def top2_cosine_gaps(truth, fitted):
    """Per true program, the gap between its best and second-best fitted match.

    Recorded as a **distribution**, which is the part that can be honestly computed now. §5.2
    requires an `ambiguous` count but defines no threshold for it, so the distribution is the
    evidence a threshold would later be calibrated against — gathering it first and choosing
    the constant second is the right order, and it is the order that was available here.
    """
    if truth.space != fitted.space:
        raise UnitMismatch(f"{truth.space!r} vs {fitted.space!r}; align before scoring")
    if truth.gene_labels != fitted.gene_labels:
        raise UnitMismatch("different gene axes; align with .subset_genes() first")
    t = _rows_unit_norm(np.asarray(truth.matrix, dtype=float))
    f = _rows_unit_norm(np.asarray(fitted.matrix, dtype=float))
    cos = t @ f.T
    if cos.shape[1] < 2:
        # With one fitted program there is no second best, so no gap is defined. Returning
        # zeros would read as "maximally ambiguous", which is a different claim.
        raise ValueError("top-2 gaps need at least 2 fitted programs")
    ordered = np.sort(cos, axis=1)
    return tuple(float(g) for g in ordered[:, -1] - ordered[:, -2])


def ambiguous_program_count(gaps, threshold=AMBIGUITY_THRESHOLD):
    """The §5.2 `ambiguous` count. **Refuses while its threshold is null**, like the above."""
    if threshold is None:
        raise ThresholdNotCalibrated(
            "the `ambiguous` count needs a top-2 cosine gap threshold that PROTOCOL §5.2 "
            "requires but does not define. Refusing rather than inventing one, having "
            "already seen this data. Use top2_cosine_gaps() to record the distribution; "
            "batch the constant into the v1.1 amendment alongside `delta` and the "
            "precision/recall threshold."
        )
    if threshold < 0:
        raise ValueError(f"threshold must be >= 0, got {threshold}")
    return int(sum(1 for g in gaps if g < threshold))


# ------------------------------------------------- gene-set recovery (v1.2, P4)

TOP_GENES_N = 50  # PROTOCOL §5.5: Gavish et al. 2023 precedent, frozen pre-results.


def top_genes(matrix, gene_labels, n=TOP_GENES_N):
    """Top-`n` genes per program by loading weight. Deterministic: ties resolve
    to the lexicographically smaller gene label, so the set is a pure function
    of the matrix rather than of row order or quicksort whims."""
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2-D, got shape {matrix.shape}")
    if matrix.shape[1] != len(gene_labels):
        raise ValueError(
            f"matrix has {matrix.shape[1]} columns but {len(gene_labels)} labels")
    if not 1 <= int(n) <= len(gene_labels):
        raise ValueError(f"n must lie in [1, n_genes], got {n}")
    labels = [str(g) for g in gene_labels]
    sets = []
    for row in matrix:
        order = sorted(range(len(labels)), key=lambda j: (-row[j], labels[j]))
        sets.append(frozenset(labels[j] for j in order[: int(n)]))
    return sets


def _jaccard(a, b):
    union = a | b
    return 1.0 if not union else float(len(a & b) / len(union))


def recovery_jaccard(true_sets, fitted_sets):
    """`program_recovery_jaccard_v1`: Hungarian maximum-weight one-to-one matching
    on Jaccard similarities, dummy factors absorbing unmatched programs on either
    side, score `Σ(matched) / max(K_true, K_fitted)` — the cosine metric's
    discipline (§5.2) transported to gene sets, for whole-workflow comparator
    rows where full loading vectors do not exist on both sides (SOURCE_AUDIT
    §2.3). Both arguments are sequences of gene-name sets (frozensets or sets);
    names are compared as strings. Returns `(score, true_to_fitted, cosines)` —
    `cosines` carries the matched Jaccard values in the truth's order so that
    callers reuse one matching object, the way `usage_error` reuses `Alignment`.
    """
    t = [set(s) for s in true_sets]
    f = [set(s) for s in fitted_sets]
    n_true, n_fitted = len(t), len(f)
    if n_true < 1 or n_fitted < 1:
        raise ValueError("need at least one true and one fitted gene set")
    sim = np.array([[ _jaccard(a, b) for b in f] for a in t])
    size = max(n_true, n_fitted)
    padded = np.zeros((size, size), dtype=float)
    padded[:n_true, :n_fitted] = sim
    rows, cols = linear_sum_assignment(-padded)
    true_to_fitted, matched = [None] * n_true, [0.0] * n_true
    total = 0.0
    for r, c in zip(rows, cols):
        if r < n_true and c < n_fitted:
            true_to_fitted[r] = int(c)
            matched[r] = float(sim[r, c])
            total += float(sim[r, c])
    return float(total / size), tuple(true_to_fitted), tuple(matched)
