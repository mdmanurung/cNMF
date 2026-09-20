"""P2-02 B scenarios: imbalance realized, balance uniform, context restricted.

Generative checks only — no inference runs here. Each property is measured on
simulated SMOKE datasets, which is cheap and exactly what the scenario
overrides promise.
"""
import numpy as np

from cnmfbench.scenarios import build_params, seed_for
from cnmfbench.simulate import simulate


def _donor_counts(ds):
    donors = np.asarray(ds.adata.obs["donor_id"])
    _, counts = np.unique(donors, return_counts=True)
    return counts


def test_imbalanced_spreads_cells_across_donors():
    ds = simulate(build_params("B_imbalanced", "SMOKE"), "B_imbalanced",
                  "SMOKE", seed_for("SMOKE"))
    counts = _donor_counts(ds)
    assert counts.max() / counts.min() >= 2.0, counts


def test_balanced_keeps_cells_even():
    ds = simulate(build_params("B_balanced", "SMOKE"), "B_balanced",
                  "SMOKE", seed_for("SMOKE"))
    counts = _donor_counts(ds)
    assert (counts == counts[0]).all(), counts


def test_context_restricts_activity_to_a_subgroup():
    ds = simulate(build_params("B_context", "SMOKE"), "B_context",
                  "SMOKE", seed_for("SMOKE"))
    assert ds.donor_eligibility is not None
    # Per-donor × identity-program eligibility mask (SMOKE: 8 donors × 2 programs).
    assert np.asarray(ds.donor_eligibility).shape == (8, 2)
    # The activity program (appended after the identity ones) is exactly absent
    # outside its eligible subgroup — the preservation target B must not lose.
    u = np.asarray(ds.true_usages)
    donors = np.asarray(ds.adata.obs["donor_id"])
    carriers = [d for d in sorted(set(donors)) if u[donors == d, -1].sum() > 0]
    assert 0 < len(carriers) < len(set(donors)), carriers
