"""Features B and C.

The first test in this file is the one the others depend on. Feature C reimplements
upstream's consensus aggregation harness-side, because `src/cnmf/**` may not be edited. If
that reimplementation does not reproduce upstream when C is OFF, then every `000` vs `001`
comparison measures the reimplementation rather than the feature, and C's effect is
uninterpretable. So it is pinned against `cnmf.consensus` on a real factor bank, not against
a mock.
"""
import numpy as np
import pandas as pd
import pytest

from cnmfbench.features import (
    consensus_spectra_from_bank,
    discovery_sample,
    run_of,
)


# --------------------------------------------------------- C: the equivalence that matters

def _tiny_bank(n_iter=8, k=4, n_genes=30, seed=0):
    """A bank with genuine cluster structure, labelled the way cNMF labels one."""
    rng = np.random.default_rng(seed)
    base = rng.random((k, n_genes)) ** 2 + 0.05
    rows, labels = [], []
    for it in range(n_iter):
        for t in range(k):
            rows.append(base[t] * rng.uniform(0.9, 1.1, n_genes))
            labels.append(f"iter{it}_topic{t + 1}")
    return pd.DataFrame(np.array(rows), index=labels,
                        columns=[f"g{i}" for i in range(n_genes)])


def test_c_off_reproduces_upstream_consensus_on_a_real_factor_bank():
    """THE LOAD-BEARING TEST. Runs real cNMF, then checks that this module's OFF path equals
    `cnmf.consensus`'s own `median_spectra` for the same k. Skips only if no bank exists."""
    import glob
    import os

    from cnmf import load_df_from_npz

    banks = sorted(glob.glob(
        "/exports/para-lipg-hpc/mdmanurung/cnmf-realdata/kang_run/kang2018/cnmf_tmp/"
        "kang2018.spectra.k_*.merged.df.npz"))
    if not banks:
        pytest.skip("no real factor bank available in this checkout")
    bank_path = banks[0]
    k = int(os.path.basename(bank_path).split("k_")[1].split(".")[0])
    merged = load_df_from_npz(bank_path)
    n_iter = merged.shape[0] // k

    consensus_path = bank_path.replace(".merged.df.npz", ".dt_2_0.consensus.df.npz")
    if not os.path.exists(consensus_path):
        pytest.skip("upstream consensus artifact not present beside the bank")
    upstream = load_df_from_npz(consensus_path)

    mine, info = consensus_spectra_from_bank(merged, k=k, density_threshold=2.0,
                                             n_iter=n_iter, one_per_run=False)
    assert info["one_per_run"] is False
    # Upstream reorders programs by total usage and renames them 1..K after this step, so
    # compare the SETS of spectra, matched by best correspondence, not row order.
    a = np.sort(upstream.values, axis=0)
    b = np.sort(mine.values, axis=0)
    rel = np.linalg.norm(a - b) / np.linalg.norm(a)
    assert rel < 1e-10, (
        f"C's OFF path diverges from upstream by relative Frobenius {rel:.3e}. Every "
        "000-vs-001 comparison would measure this divergence rather than feature C."
    )


def test_c_off_and_on_differ_only_by_the_dedup_step():
    bank = _tiny_bank()
    off, ioff = consensus_spectra_from_bank(bank, k=4, density_threshold=2.0, n_iter=8)
    on, ion = consensus_spectra_from_bank(bank, k=4, density_threshold=2.0, n_iter=8,
                                          one_per_run=True)
    assert ioff["n_after_density"] == ion["n_after_density"], "density filter must not move"
    assert ioff["n_neighbors"] == ion["n_neighbors"]
    assert on.shape == off.shape
    assert "n_dropped_duplicate_contributions" in ion


def test_c_drops_a_duplicate_contribution_when_one_run_splits_a_program():
    """C's entire purpose. A run that contributes twice to one cluster must vote once."""
    bank = _tiny_bank(n_iter=6, k=3)
    # Make iter0 split cluster 1: its topic2 becomes a near-copy of its topic1.
    bank.loc["iter0_topic2"] = bank.loc["iter0_topic1"].values * 1.001
    _, info = consensus_spectra_from_bank(bank, k=3, density_threshold=2.0, n_iter=6,
                                          one_per_run=True)
    assert info["n_dropped_duplicate_contributions"] >= 1


def test_rows_sum_to_one_in_both_modes():
    bank = _tiny_bank()
    for flag in (False, True):
        m, _ = consensus_spectra_from_bank(bank, k=4, density_threshold=2.0, n_iter=8,
                                           one_per_run=flag)
        assert np.allclose(m.values.sum(axis=1), 1.0, atol=1e-12)
        assert np.all(m.values >= 0)


def test_run_identity_refuses_an_unrecognised_label():
    """If upstream changed the label format, C would silently mean 'one per something else'."""
    with pytest.raises(ValueError, match="iter<N>_topic<M>"):
        run_of(["cluster_0", "cluster_1"])
    assert list(run_of(["iter0_topic1", "iter12_topic3"])) == ["iter0", "iter12"]


def test_a_degenerate_neighborhood_raises_rather_than_dividing_by_zero():
    bank = _tiny_bank(n_iter=2, k=4)  # int(0.30 * 8 / 4) = 0
    with pytest.raises(ValueError, match="divides by zero"):
        consensus_spectra_from_bank(bank, k=4, density_threshold=2.0, n_iter=2)


# --------------------------------------------------------------------------- B: the sampling

def _cells(sizes):
    ids, donors = [], []
    for d, n in sizes.items():
        ids += [f"{d}_c{i}" for i in range(n)]
        donors += [d] * n
    return ids, donors


def test_b_on_gives_every_donor_the_same_number_of_cells():
    ids, donors = _cells({"d0": 100, "d1": 100, "d2": 100, "d3": 100})
    s = discovery_sample(ids, donors, budget=80, equal_per_donor=True, seed=1)
    assert len(s) == 80
    assert set(s.per_donor.values()) == {20}
    assert s.mode == "equal_per_donor_without_replacement"


def test_both_arms_draw_exactly_the_same_budget():
    """The matched-budget premise. An unequal draw would confound B with sample size."""
    ids, donors = _cells({"d0": 500, "d1": 100, "d2": 50, "d3": 20})
    for flag in (False, True):
        assert len(discovery_sample(ids, donors, 200, flag, seed=3)) == 200


def test_b_off_tracks_donor_sizes_and_b_on_does_not():
    ids, donors = _cells({"big": 800, "small": 80})
    off = discovery_sample(ids, donors, 200, equal_per_donor=False, seed=5)
    on = discovery_sample(ids, donors, 200, equal_per_donor=True, seed=5)
    assert off.per_donor["big"] > 3 * off.per_donor["small"], "proportional should be skewed"
    assert on.per_donor["small"] > off.per_donor["small"], "B must lift the small donor"


def test_a_donor_short_of_its_equal_share_contributes_everything_and_the_rest_is_redistributed():
    """Without redistribution, equal_per_donor would quietly shrink the budget whenever
    donors are uneven, and the two arms would stop being matched."""
    ids, donors = _cells({"big": 500, "tiny": 7})
    s = discovery_sample(ids, donors, 200, equal_per_donor=True, seed=7)
    assert len(s) == 200
    assert s.per_donor["tiny"] == 7, "a donor with 7 cells cannot give 100"
    assert s.per_donor["big"] == 193


def test_the_draw_is_deterministic_in_its_seed_and_independent_of_rank():
    ids, donors = _cells({"d0": 60, "d1": 90, "d2": 30})
    a = discovery_sample(ids, donors, 60, True, seed=11).cell_ids
    b = discovery_sample(ids, donors, 60, True, seed=11).cell_ids
    c = discovery_sample(ids, donors, 60, True, seed=12).cell_ids
    assert a == b, "same seed must give the same discovery cells at every rank"
    assert a != c


def test_sampling_is_without_replacement():
    ids, donors = _cells({"d0": 40, "d1": 40})
    s = discovery_sample(ids, donors, 50, True, seed=13)
    assert len(set(s.cell_ids)) == len(s.cell_ids) == 50


def test_an_impossible_budget_raises():
    ids, donors = _cells({"d0": 10})
    with pytest.raises(ValueError, match="outside"):
        discovery_sample(ids, donors, 99, True, seed=1)


def test_c_on_is_identical_when_no_run_contributes_twice():
    """P3-03 no-op property: where the constraint already holds, C changes nothing.
    (End-to-end this is why C-ON == C-OFF bitwise at/below K_true.)"""
    bank = _tiny_bank()
    off, _ = consensus_spectra_from_bank(bank, k=4, density_threshold=2.0, n_iter=8)
    on, info = consensus_spectra_from_bank(bank, k=4, density_threshold=2.0, n_iter=8,
                                           one_per_run=True)
    assert info["n_dropped_duplicate_contributions"] == 0
    assert np.array_equal(np.sort(off.values, axis=0), np.sort(on.values, axis=0))


def test_c_refuses_a_bank_with_a_failed_fit_rather_than_dropping_it_silently():
    """P3-03 incomplete-run handling: a NaN factor (failed optimizer run) must raise,
    never vanish from the consensus without a recorded reason."""
    bank = _tiny_bank()
    bank.iloc[0, :] = np.nan
    with pytest.raises(ValueError, match="[Nn]aN"):
        consensus_spectra_from_bank(bank, k=4, density_threshold=2.0, n_iter=8,
                                    one_per_run=True)
