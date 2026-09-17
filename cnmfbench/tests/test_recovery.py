"""The recovery metric, and the corruption battery that says what it must not do.

The battery is the point. A metric that only gets tested on "does a good fit score high"
passes while being invariant to nothing and sensitive to everything. Here the invariances are
tested exactly as strictly as the penalties: relabelling programs, reordering genes and
rescaling a factor must change the score by **zero**, because all three are the same solution
written differently.
"""
import numpy as np
import pytest

from cnmfbench.recovery import (
    Spectra,
    UnitMismatch,
    matched_null_spectra,
    recovery_cosine,
    usage_error,
)

GENES = tuple(f"g{i}" for i in range(12))


def _truth(k=3, n_genes=12, seed=0):
    rng = np.random.default_rng(seed)
    m = rng.random((k, n_genes)) ** 3  # peaked, so programs are distinguishable
    m /= m.sum(axis=1, keepdims=True)
    return Spectra(matrix=m, space="count", gene_labels=GENES[:n_genes])


# ------------------------------------------------------------------ units are the result

def test_comparing_across_spaces_raises_instead_of_scoring():
    """The measured consequence of not raising: the null beats the fit at every rank."""
    truth = _truth()
    fitted = Spectra(matrix=truth.matrix.copy(), space="scaled", gene_labels=truth.gene_labels)
    with pytest.raises(UnitMismatch, match="shear"):
        recovery_cosine(truth, fitted)


def test_the_two_alignment_routes_agree():
    """Pushing truth into scaled space and pulling the fit into count space must give the
    same score. Their agreement is the evidence that either is correct."""
    rng = np.random.default_rng(3)
    truth = _truth()
    s_g = rng.uniform(0.2, 5.0, size=len(truth.gene_labels))
    fitted_scaled = Spectra(
        matrix=(truth.matrix / s_g) * rng.uniform(0.5, 2.0, size=(3, 1)),
        space="scaled", gene_labels=truth.gene_labels,
    )
    push, _ = recovery_cosine(truth.to_scaled(s_g), fitted_scaled)
    pull, _ = recovery_cosine(truth, fitted_scaled.to_count(s_g))
    assert push == pytest.approx(pull, abs=1e-12)


def test_different_gene_axes_raise():
    truth = _truth(n_genes=12)
    fitted = Spectra(matrix=np.ones((3, 6)), space="count", gene_labels=GENES[:6])
    with pytest.raises(UnitMismatch, match="gene axes"):
        recovery_cosine(truth, fitted)


def test_subset_genes_refuses_to_silently_intersect():
    truth = _truth()
    with pytest.raises(UnitMismatch, match="absent"):
        truth.subset_genes(["g0", "not_a_gene"])


# ------------------------------------------------------------------ INVARIANCES: must be exact

def test_permuting_program_labels_is_invariant():
    truth = _truth()
    fitted = Spectra(truth.matrix.copy(), "count", truth.gene_labels)
    base, _ = recovery_cosine(truth, fitted)
    perm = Spectra(truth.matrix[[2, 0, 1]], "count", truth.gene_labels)
    assert recovery_cosine(truth, perm)[0] == pytest.approx(base, abs=1e-12)


def test_reordering_genes_is_invariant():
    truth = _truth()
    fitted = Spectra(truth.matrix.copy(), "count", truth.gene_labels)
    base, _ = recovery_cosine(truth, fitted)
    order = [7, 0, 3, 11, 2, 9, 1, 5, 8, 4, 10, 6]
    labels = tuple(truth.gene_labels[i] for i in order)
    assert recovery_cosine(
        Spectra(truth.matrix[:, order], "count", labels),
        Spectra(fitted.matrix[:, order], "count", labels),
    )[0] == pytest.approx(base, abs=1e-12)


def test_rescaling_a_factor_is_invariant():
    """A factor scaled by c with its usage scaled by 1/c is the same solution. Cosine is
    scale-invariant per row, and this pins that it stays so through the matching."""
    truth = _truth()
    fitted = Spectra(truth.matrix * np.array([[1.0], [17.0], [0.03]]), "count", truth.gene_labels)
    assert recovery_cosine(truth, fitted)[0] == pytest.approx(1.0, abs=1e-12)


# ------------------------------------------------------------------ PENALTIES

def test_a_perfect_fit_scores_one():
    truth = _truth()
    assert recovery_cosine(truth, Spectra(truth.matrix.copy(), "count", truth.gene_labels))[0] \
        == pytest.approx(1.0, abs=1e-12)


def test_duplicating_a_factor_is_penalised():
    """K=4 built by copying one true program twice cannot score as well as K=3 exact: the
    denominator is max(K_true, K_fitted) and the duplicate matches a dummy."""
    truth = _truth()
    dup = np.vstack([truth.matrix, truth.matrix[0:1]])
    score, align = recovery_cosine(truth, Spectra(dup, "count", truth.gene_labels))
    assert score == pytest.approx(3.0 / 4.0, abs=1e-12)
    assert len(align.unmatched_fitted) == 1


def test_deleting_a_true_program_is_penalised():
    truth = _truth()
    score, align = recovery_cosine(
        truth, Spectra(truth.matrix[:2].copy(), "count", truth.gene_labels))
    assert score == pytest.approx(2.0 / 3.0, abs=1e-12)
    assert align.unmatched_true == (2,)


def test_replacing_the_solution_by_noise_lands_near_the_matched_null():
    """The pre-registered requirement is 'penalise hard, landing near the matched null' --
    not 'score zero'. Nonnegative random vectors are not orthogonal to anything."""
    rng = np.random.default_rng(11)
    truth = _truth()
    noise = Spectra(rng.random((3, 12)), "count", truth.gene_labels)
    null = matched_null_spectra(truth, 3)
    noise_score, _ = recovery_cosine(truth, noise)
    null_score, _ = recovery_cosine(truth, null)
    perfect, _ = recovery_cosine(truth, Spectra(truth.matrix.copy(), "count", truth.gene_labels))
    assert noise_score < perfect
    assert abs(noise_score - null_score) < 0.25


# ------------------------------------------------------------------ the matched null

def test_the_matched_null_is_well_below_a_perfect_fit_but_far_above_zero():
    """Why the null must be reported beside every recovery row: its floor is high. Measured
    at SMOKE it was 0.850 at K_true, so an unaccompanied 0.87 reads as strong and is not."""
    truth = _truth()
    null_score, _ = recovery_cosine(truth, matched_null_spectra(truth, 3))
    assert 0.0 < null_score < 1.0
    assert recovery_cosine(
        truth, Spectra(truth.matrix.copy(), "count", truth.gene_labels))[0] > null_score


def test_the_null_inherits_the_space_so_it_cannot_drift_out_of_units():
    truth = _truth()
    s_g = np.linspace(0.5, 3.0, 12)
    aligned = truth.to_scaled(s_g)
    assert matched_null_spectra(aligned, 4).space == "scaled"
    recovery_cosine(aligned, matched_null_spectra(aligned, 4))  # must not raise


def test_the_null_is_recomputed_per_rank_not_carried_as_a_constant():
    truth = _truth()
    scores = {k: recovery_cosine(truth, matched_null_spectra(truth, k))[0] for k in (2, 3, 5)}
    assert len(set(scores.values())) > 1, "null must move with K; a constant floor would mislead"


# ------------------------------------------------------------------ the alignment object

def test_alignment_is_one_to_one():
    truth = _truth(k=4)
    rng = np.random.default_rng(5)
    fitted = Spectra(rng.random((4, 12)), "count", truth.gene_labels)
    _, align = recovery_cosine(truth, fitted)
    assigned = [j for j in align.true_to_fitted if j is not None]
    assert len(assigned) == len(set(assigned))


def test_a_zero_program_scores_zero_rather_than_raising():
    truth = _truth()
    fitted = Spectra(np.vstack([truth.matrix[:2], np.zeros((1, 12))]), "count", truth.gene_labels)
    score, align = recovery_cosine(truth, fitted)
    assert 0.0 <= score <= 1.0
    assert min(align.cosines) == pytest.approx(0.0, abs=1e-12)


# ------------------------------------------------------------------ usage_error_v1

def _usages(n_cells=40, k=3, seed=1):
    rng = np.random.default_rng(seed)
    u = rng.random((n_cells, k))
    return u / u.sum(axis=1, keepdims=True)


def test_usage_error_is_zero_for_an_exact_recovery():
    truth = _truth()
    _, align = recovery_cosine(truth, Spectra(truth.matrix.copy(), "count", truth.gene_labels))
    u = _usages()
    assert usage_error(u, u, align)[0] == pytest.approx(0.0, abs=1e-12)


def test_usage_error_reuses_the_alignment_and_survives_a_permuted_fit():
    """The permutation is carried by the alignment object, so relabelling the fit's programs
    changes nothing — which is only true because the matching is not re-derived here."""
    truth = _truth()
    perm = [2, 0, 1]
    fitted = Spectra(truth.matrix[perm], "count", truth.gene_labels)
    _, align = recovery_cosine(truth, fitted)
    u = _usages()
    assert usage_error(u, u[:, perm], align)[0] == pytest.approx(0.0, abs=1e-12)


def test_usage_error_refuses_an_alignment_from_a_different_fit():
    """A mismatched alignment would score one solution's usages against another's matching."""
    truth = _truth()
    _, align = recovery_cosine(truth, Spectra(truth.matrix.copy(), "count", truth.gene_labels))
    with pytest.raises(ValueError, match="alignment was computed on"):
        usage_error(_usages(), _usages(k=4, seed=2), align)


def test_shuffling_usages_is_penalised_while_recovery_is_unchanged():
    """The pre-registered requirement: corrupting usages must move usage error and leave
    recovery alone, since recovery reads only the spectra."""
    rng = np.random.default_rng(7)
    truth = _truth()
    fitted = Spectra(truth.matrix.copy(), "count", truth.gene_labels)
    score_before, align = recovery_cosine(truth, fitted)
    u = _usages()
    shuffled = u[rng.permutation(u.shape[0])]
    assert usage_error(u, shuffled, align)[0] > usage_error(u, u, align)[0]
    assert recovery_cosine(truth, fitted)[0] == pytest.approx(score_before, abs=1e-12)


def test_a_missing_true_program_is_retained_as_error_not_dropped():
    """Dropping it would reward a fit for omitting what it could not model."""
    truth = _truth()
    _, align = recovery_cosine(truth, Spectra(truth.matrix[:2].copy(), "count", truth.gene_labels))
    u = _usages()
    err, _ = usage_error(u, u[:, :2], align)
    assert err > 0.0


def test_usage_error_is_invariant_to_per_cell_rescaling():
    """Usages are defined up to a per-cell scale; cNMF's are not normalised to sum to 1."""
    truth = _truth()
    _, align = recovery_cosine(truth, Spectra(truth.matrix.copy(), "count", truth.gene_labels))
    u = _usages()
    scaled = u * np.linspace(0.1, 9.0, u.shape[0])[:, None]
    assert usage_error(u, scaled, align)[0] == pytest.approx(0.0, abs=1e-12)
