"""The simulator is the ground truth for every later metric, so it is validated rather
than assumed. A wrong simulator is the one error no downstream test can detect.
"""
import dataclasses

import numpy as np
import pytest

from cnmfbench.contract import ContractViolation, check_dataset
from cnmfbench.scenarios import build_params, seed_for
from cnmfbench.simulate import build_spectra, simulate

TIER = "SMOKE"


@pytest.fixture(scope="module")
def params():
    return build_params("base_identifiable", TIER)


@pytest.fixture(scope="module")
def dataset(params):
    return simulate(params, "base_identifiable", TIER, seed_for(TIER))


# --------------------------------------------------------------------------- contract


def test_dataset_satisfies_the_data_contract(dataset):
    check_dataset(dataset.adata, dataset.true_spectra, dataset.true_usages)


def test_counts_are_cells_by_genes(dataset, params):
    assert dataset.adata.shape == (dataset.adata.n_obs, params.n_genes)


def test_truth_is_stored_alongside_counts_not_inside_them(dataset):
    # §6.3: ground truth is never an input to any selector, transform or fit. Keeping it
    # off `adata` entirely is the cheapest way to make accidental use impossible.
    assert "true_usages" not in dataset.adata.obsm
    assert not any("true" in c for c in dataset.adata.obs.columns)


def test_expected_counts_match_the_truth_product(dataset):
    np.testing.assert_allclose(
        dataset.expected_counts, dataset.true_usages @ dataset.true_spectra, rtol=1e-10
    )


# ------------------------------------------------------- emptiness, at the worst depth


@pytest.mark.parametrize("scenario", ["base_identifiable", "A_weak", "A_null"])
def test_no_empty_cells_or_genes_at_lowest_depth(scenario):
    """Checked at the lowest configured depth, which is where it would first bite.

    An all-zero cell makes `get_norm_counts` raise (`cnmf.py:551-554`); an all-zero gene
    makes `gene_fano = gene_var/gene_mean` NaN (`cnmf.py:144`) and that NaN propagates
    silently into HVG selection. Post-hoc filtering is not an acceptable fix because it
    is data-dependent and would touch held-out cells, so the generator must guarantee the
    property itself.
    """
    base = build_params(scenario, TIER)
    lean = dataclasses.replace(base, mean_library=400.0, min_library=200)
    ds = simulate(lean, scenario, TIER, seed=4242)
    x = np.asarray(ds.adata.X)
    assert (x.sum(axis=1) == 0).sum() == 0
    assert (x.sum(axis=0) == 0).sum() == 0


# ------------------------------------------------------------ determinism, replication


def test_same_seed_reproduces_bitwise(params):
    a = simulate(params, "base_identifiable", TIER, seed=99)
    b = simulate(params, "base_identifiable", TIER, seed=99)
    np.testing.assert_array_equal(np.asarray(a.adata.X), np.asarray(b.adata.X))
    np.testing.assert_array_equal(a.true_spectra, b.true_spectra)
    assert a.dataset_manifest_hash == b.dataset_manifest_hash


def test_replicate_changes_the_whole_draw_not_only_the_noise(params):
    """A replicate must be an independent dataset from the same model, not a reseeded
    rerun of the same structure — otherwise a variability estimate built from replicates
    understates the variability it claims to measure."""
    a = simulate(params, "base_identifiable", TIER, seed=99, simulation_replicate=0)
    b = simulate(params, "base_identifiable", TIER, seed=99, simulation_replicate=1)
    assert not np.array_equal(np.asarray(a.adata.X), np.asarray(b.adata.X))
    assert not np.allclose(a.true_spectra, b.true_spectra)
    assert not np.array_equal(a.donor_eligibility, b.donor_eligibility)


# --------------------------------------------------------------- §6.6 manifest hashing


def test_manifest_hash_is_seed_sensitive(params):
    a = simulate(params, "base_identifiable", TIER, seed=1)
    b = simulate(params, "base_identifiable", TIER, seed=2)
    assert a.dataset_manifest_hash != b.dataset_manifest_hash


def test_manifest_hash_is_replicate_sensitive(params):
    a = simulate(params, "base_identifiable", TIER, seed=1, simulation_replicate=0)
    b = simulate(params, "base_identifiable", TIER, seed=1, simulation_replicate=1)
    assert a.dataset_manifest_hash != b.dataset_manifest_hash


def test_manifest_hash_is_parameter_sensitive(params):
    a = simulate(params, "base_identifiable", TIER, seed=1)
    nudged = dataclasses.replace(params, lambda_separation=params.lambda_separation + 0.5)
    b = simulate(nudged, "base_identifiable", TIER, seed=1)
    assert a.dataset_manifest_hash != b.dataset_manifest_hash


def test_manifest_hash_is_scenario_and_tier_sensitive(params):
    a = simulate(params, "base_identifiable", TIER, seed=1)
    b = simulate(params, "A_weak", TIER, seed=1)
    c = simulate(params, "base_identifiable", "DEVELOPMENT", seed=1)
    assert len({a.dataset_manifest_hash, b.dataset_manifest_hash, c.dataset_manifest_hash}) == 3


def test_manifest_records_the_protocol_version(dataset):
    # Two datasets generated under different protocol versions must not collide even if
    # every other input matches: the contract their counts satisfy is not the same.
    assert dataset.manifest["protocol_version"]


# ----------------------------------------------------------------- generative guardrails


def test_poisson_counts_converge_to_lambda_at_high_depth(params):
    deep = dataclasses.replace(params, mean_library=200_000.0)
    ds = simulate(deep, "base_identifiable", TIER, seed=7)
    x = np.asarray(ds.adata.X, dtype=float)
    lam = ds.expected_counts
    # A Poisson draw has sd = sqrt(lambda), so the relative deviation shrinks as
    # 1/sqrt(lambda). This checks the observation model is actually Poisson and that
    # `Lambda` is its expectation parameter, not a realised total.
    keep = lam > 50
    z = (x[keep] - lam[keep]) / np.sqrt(lam[keep])
    assert abs(z.mean()) < 0.1
    assert 0.8 < z.std() < 1.25


def test_background_genes_have_across_program_variance(dataset, params):
    """Guards the HVG oracle failure: with zero across-program variance on background
    genes, Fano-based HVG selection becomes a perfect marker detector and the gene panel
    is unrealistically easy."""
    marker = np.zeros(params.n_genes, dtype=bool)
    for m in dataset.marker_sets:
        marker[m] = True
    v = dataset.true_spectra
    background_cv = (v[:, ~marker].std(axis=0) / v[:, ~marker].mean(axis=0)).mean()
    assert background_cv > 0.05


def test_spectra_rank_is_checked_before_counts_are_drawn(params):
    """`rank(V) == K_true` is fixed by marker-set combinatorics; no value of lambda
    repairs a deficiency. Zero separation collapses every program onto the same
    background direction up to the per-gene jitter, which is the degenerate case the
    check exists to catch."""
    degenerate = dataclasses.replace(
        params, lambda_separation=0.0, background_program_cv=1e-12
    )
    with pytest.raises((ContractViolation, ValueError)):
        build_spectra(degenerate, np.random.default_rng(0))


def test_every_program_is_present_in_at_least_one_donor(dataset):
    # A program eligible in no donor is absent from the dataset entirely, and
    # program_recovery_cosine_v1 would then score a program that was never generated.
    assert dataset.donor_eligibility.any(axis=0).all()


def test_every_donor_has_at_least_one_eligible_program(dataset):
    assert dataset.donor_eligibility.any(axis=1).all()


def test_rare_programs_are_weakly_represented_not_absent():
    """Coverage must span universal / common / rare simultaneously (SOURCE_AUDIT §2.5).
    A dataset of only rare programs would be discarded wholesale by a comparator
    configured as published, which would look like a failure of the method rather than of
    the setting."""
    p = build_params("base_identifiable", "DEVELOPMENT")
    ds = simulate(p, "base_identifiable", "DEVELOPMENT", seed_for("DEVELOPMENT"))
    coverage = ds.donor_eligibility.mean(axis=0)
    assert coverage.max() > 0.9, "no universal program"
    assert coverage.min() < 0.3, "no rare program"
    assert ((coverage > 0.3) & (coverage < 0.9)).any(), "no common program"
