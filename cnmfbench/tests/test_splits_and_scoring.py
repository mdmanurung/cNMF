"""Splitter and scorer: the rules that produce a plausible wrong number if violated.

Several of these exist because the reference implementation they replace
(`diagnostics._score_split` and `donor_blocking_gap`) gets them wrong, and the tracker
tells the next session to read that file first.
"""
import numpy as np
import pytest

from cnmfbench.contract import ContractViolation
from cnmfbench.scoring import (
    count_unit_error, equal_donor_mean, nnls_usages, null_dictionary, scoreable_mask,
    squared_prediction_error, to_training_scale, training_gene_scale,
)
from cnmfbench.splits import gene_panel, outer_donor_folds

DONORS = [f"donor_{i:03d}" for i in range(8)]
GENES = [f"gene_{i:05d}" for i in range(100)]


# ------------------------------------------------------------------------------ splits


def test_every_donor_is_a_test_donor_exactly_once():
    folds = outer_donor_folds(DONORS, 2, seed=7)
    appearances = [d for f in folds for d in f.test_donors]
    assert sorted(appearances) == sorted(DONORS)


def test_train_and_test_donors_are_disjoint():
    for f in outer_donor_folds(DONORS, 2, seed=7):
        assert not (set(f.train_donors) & set(f.test_donors))


def test_folds_are_deterministic_from_the_seed():
    assert outer_donor_folds(DONORS, 2, 7) == outer_donor_folds(DONORS, 2, 7)
    assert outer_donor_folds(DONORS, 2, 7) != outer_donor_folds(DONORS, 2, 8)


def test_folds_are_independent_of_input_donor_order():
    # A split that depended on the order donors happened to arrive in would silently
    # change when the simulator's cell ordering changed.
    assert outer_donor_folds(DONORS, 2, 7) == outer_donor_folds(list(reversed(DONORS)), 2, 7)


def test_panel_partitions_G_exactly():
    p = gene_panel(GENES, 0.5, panel_seed=4242)
    assert set(p.inference_genes) | set(p.validation_genes) == set(GENES)
    assert not (set(p.inference_genes) & set(p.validation_genes))
    assert len(p.inference_genes) == 50


def test_mask_id_hashes_the_realised_panel_not_the_gene_order():
    """§4.1's "identical panels" must be checkable by equality, so `mask_id` identifies
    the panel itself. cNMF's G comes back in Fano-ranked order; a reordering that left
    the panel identical must not change the id."""
    a = gene_panel(GENES, 0.5, 4242)
    b = gene_panel(list(reversed(GENES)), 0.5, 4242)
    assert a.mask_id == b.mask_id
    assert a.inference_genes == b.inference_genes


def test_mask_id_is_sensitive_to_the_panel_seed_and_the_fraction():
    base = gene_panel(GENES, 0.5, 4242)
    assert base.mask_id != gene_panel(GENES, 0.5, 4243).mask_id
    assert base.mask_id != gene_panel(GENES, 0.6, 4242).mask_id


def test_panel_does_not_depend_on_expression():
    """§4.2: panels must cover zeros as well as nonzeros. A panel conditioned on
    expression level would be data-dependent, which is forbidden. The signature takes no
    count matrix at all, which is the structural guarantee — this pins it."""
    import inspect

    assert "counts" not in inspect.signature(gene_panel).parameters


def test_panel_rejects_a_fraction_that_empties_a_side():
    with pytest.raises(ValueError):
        gene_panel(GENES, 0.001, 1)


# ----------------------------------------------------------------------------- scoring


def test_training_gene_scale_is_ddof_one():
    x = np.array([[1.0, 2.0], [3.0, 8.0], [5.0, 2.0]])
    np.testing.assert_allclose(training_gene_scale(x), x.std(axis=0, ddof=1))


def test_training_gene_scale_raises_on_a_zero_variance_gene():
    """`diagnostics.training_gene_std` floors these to 1.0, matching cNMF's sparse
    branch; the dense branch divides by zero and only prints a warning. Flooring here
    would put the harness's X in different units from the dictionary on that gene."""
    x = np.array([[1.0, 5.0], [3.0, 5.0], [7.0, 5.0]])
    with pytest.raises(ContractViolation, match="zero variance"):
        training_gene_scale(x)


def test_nnls_recovers_a_known_nonnegative_solution_exactly():
    rng = np.random.default_rng(0)
    v = np.abs(rng.normal(size=(3, 20))) + 0.1
    u = np.abs(rng.normal(size=(6, 3)))
    np.testing.assert_allclose(nnls_usages(u @ v, v), u, atol=1e-10)


def test_nnls_is_nonnegative_on_signed_targets():
    rng = np.random.default_rng(1)
    v = np.abs(rng.normal(size=(2, 10))) + 0.1
    assert (nnls_usages(rng.normal(size=(5, 10)), v) >= 0).all()


def test_zero_inference_count_cell_is_excluded_not_crashed_on():
    """§4.3. cNMF raises a hard exception on zero-HVG cells (`cnmf.py:550-554`); the
    harness must degrade gracefully instead and lose only that cell.

    Measured at SMOKE this path never fires (minimum per-cell inference total is 137
    counts), so without this test a bug in it would be invisible to the smoke run.
    """
    raw = np.array([[0, 0, 0], [4, 0, 1], [0, 2, 0]])
    keep = scoreable_mask(raw)
    assert keep.tolist() == [False, True, True]


def test_equal_donor_mean_differs_from_the_pooled_cell_mean():
    loss = np.array([1.0] * 9 + [10.0])
    donors = ["a"] * 9 + ["b"]
    agg = equal_donor_mean(loss, donors)
    assert agg.value == pytest.approx(5.5)
    assert agg.value != pytest.approx(loss.mean())
    assert agg.per_donor == {"a": 1.0, "b": 10.0}


def test_equal_donor_mean_counts_are_donors_not_cells():
    agg = equal_donor_mean(np.ones(10), ["a"] * 9 + ["b"])
    assert agg.n_eligible_donors == 2


def test_equal_donor_mean_refuses_when_no_donor_has_a_scored_cell():
    with pytest.raises(ContractViolation):
        equal_donor_mean(np.array([]), [])


# ------------------------- the equal_donor_mean corruption/invariance battery (P0-04)
#
# `IMPLEMENTATION_PROMPT.md:152` requires the metrics to "penalize damaging changes and
# remain invariant to irrelevant permutations". The recovery metrics got their battery in
# `test_recovery.py`; the AGGREGATOR did not, and its fence entry said so. These are its
# own invariances, which are not the recovery metric's: the property that makes
# `equal_donor_mean` worth having — a donor's weight does not depend on its cell count —
# is invisible to any test of the metric being aggregated.


def test_equal_donor_mean_is_invariant_to_cell_order():
    rng = np.random.default_rng(0)
    loss = rng.random(60) * 10
    donors = np.array(["a", "b", "c"] * 20)
    perm = rng.permutation(60)
    base = equal_donor_mean(loss, donors)
    shuffled = equal_donor_mean(loss[perm], donors[perm])
    assert shuffled.value == pytest.approx(base.value, abs=1e-12)
    assert shuffled.per_donor == pytest.approx(base.per_donor, abs=1e-12)


def test_equal_donor_mean_is_invariant_to_donor_relabelling():
    """Donor ids are identifiers, not data. The aggregator sorts them, so a relabelling
    that reorders them must not move the value."""
    loss = np.array([1.0, 2.0, 3.0, 40.0])
    a = equal_donor_mean(loss, ["a", "a", "a", "b"])
    b = equal_donor_mean(loss, ["zzz", "zzz", "zzz", "aaa"])
    assert b.value == pytest.approx(a.value, abs=1e-12)
    assert sorted(b.per_donor.values()) == pytest.approx(sorted(a.per_donor.values()))


def test_equal_donor_mean_is_invariant_to_replicating_a_donors_cells():
    """THE PROPERTY THE AGGREGATOR EXISTS FOR. Duplicating every cell of one donor leaves
    that donor's within-donor mean unchanged, so it must not gain influence. A pooled cell
    mean would shift here, which is exactly the failure §3.5 is guarding against."""
    loss = np.array([1.0, 1.0, 10.0])
    donors = ["a", "a", "b"]
    base = equal_donor_mean(loss, donors)
    fat = equal_donor_mean(np.concatenate([loss, [1.0] * 97]), donors + ["a"] * 97)
    assert fat.value == pytest.approx(base.value, abs=1e-12)
    assert np.mean(np.concatenate([loss, [1.0] * 97])) != pytest.approx(base.value)


def test_equal_donor_mean_is_positively_homogeneous():
    """A change of units on the loss must scale the aggregate by the same factor and
    nothing else — the property D016 relies on when it reads B in count units."""
    loss = np.array([1.0, 3.0, 7.0, 11.0])
    donors = ["a", "a", "b", "c"]
    base = equal_donor_mean(loss, donors)
    scaled = equal_donor_mean(loss * 4.0, donors)
    assert scaled.value == pytest.approx(4.0 * base.value, rel=1e-12)


def test_corrupting_one_donor_moves_the_aggregate_by_exactly_its_share():
    """The penalty side. With n donors, damaging one must move the value by delta/n — not
    by delta weighted by that donor's cell count, which is what a pooled mean would do."""
    loss = np.array([1.0] * 9 + [1.0] * 1)
    donors = ["a"] * 9 + ["b"]
    base = equal_donor_mean(loss, donors)
    corrupted = loss.copy()
    corrupted[:9] += 6.0  # donor 'a', the one holding 90% of the cells
    got = equal_donor_mean(corrupted, donors)
    assert got.value - base.value == pytest.approx(6.0 / 2, abs=1e-12)


def test_an_excluded_donor_is_counted_and_never_entered_as_a_zero():
    """A zero would read as a perfect prediction and would drag the mean DOWN, turning a
    donor that could not be scored into evidence that the fit was good."""
    loss = np.array([4.0, 6.0])
    agg = equal_donor_mean(loss, ["a", "b"])
    assert agg.value == pytest.approx(5.0)
    assert agg.n_eligible_donors == 2 and agg.n_failed_donors == 0
    # A donor present in the labels but with no cells cannot arise from the array form, so
    # the guarantee is checked at the boundary the runner actually hits: an empty input.
    with pytest.raises(ContractViolation):
        equal_donor_mean(np.array([]), [])


def test_equal_donor_mean_refuses_mismatched_lengths_rather_than_broadcasting():
    with pytest.raises(ValueError, match="losses for"):
        equal_donor_mean(np.ones(5), ["a"] * 4)


def test_null_dictionary_must_be_given_scaled_input():
    """The 4x trap: the null profile must be the mean of X = raw/s_g, not of raw counts.
    Measured on SMOKE, using raw counts inflates the floor from ~24 to ~97 with no
    warning, making the model look four times better than it is."""
    raw = np.array([[10.0, 100.0], [20.0, 200.0], [30.0, 300.0]])
    s_g = training_gene_scale(raw)
    scaled_profile = null_dictionary(to_training_scale(raw, s_g))
    raw_profile = null_dictionary(raw)
    assert not np.allclose(scaled_profile, raw_profile)
    np.testing.assert_allclose(scaled_profile, (raw / s_g[None, :]).mean(axis=0, keepdims=True))


def test_null_amplitude_uses_the_inference_panel_only():
    """§3.4: the null must be "handicapped identically" — its amplitude comes from the
    same NNLS on G_inf only. Perturbing validation-panel values must not move it."""
    rng = np.random.default_rng(3)
    x = np.abs(rng.normal(size=(5, 8))) + 1.0
    v0 = null_dictionary(x)
    inf, val = np.array([0, 1, 2, 3]), np.array([4, 5, 6, 7])
    u_before = nnls_usages(x[:, inf], v0[:, inf])
    x_perturbed = x.copy()
    x_perturbed[:, val] *= 7.5
    u_after = nnls_usages(x_perturbed[:, inf], v0[:, inf])
    np.testing.assert_array_equal(u_before, u_after)


def test_perturbing_validation_genes_leaves_model_usages_bitwise_unchanged():
    """The cheapest available leakage check and a down payment on P0-05. Exact because
    the projection uses scipy.optimize.nnls rather than a tolerance-based solver."""
    rng = np.random.default_rng(4)
    v = np.abs(rng.normal(size=(3, 10))) + 0.1
    x = np.abs(rng.normal(size=(6, 10))) + 0.5
    inf, val = np.arange(5), np.arange(5, 10)
    before = nnls_usages(x[:, inf], v[:, inf])
    x2 = x.copy()
    x2[:, val] = 0.0
    np.testing.assert_array_equal(before, nnls_usages(x2[:, inf], v[:, inf]))


def test_count_unit_error_is_the_training_scale_error_times_s_g_squared():
    x = np.array([[2.0]])
    u = np.array([[0.0]])
    v = np.array([[1.0]])
    s = np.array([3.0])
    assert count_unit_error(x, u, v, s)[0] == pytest.approx(
        squared_prediction_error(x, u, v)[0] * 9.0
    )
