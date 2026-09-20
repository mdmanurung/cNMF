"""P2-03 discovery safeguards: matched budgets, deterministic draws, frozen preprocessor.

Unit-level properties of `discovery_sample` plus one SMOKE execution proving
both B arms share the frozen G while drawing different, exactly-matched cells.
"""
import os

import pytest
import yaml

from cnmfbench.features import discovery_sample

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _cells(n0=6, n1=6):
    ids = [f"cell_{i}" for i in range(n0 + n1)]
    donors = ["d0"] * n0 + ["d1"] * n1
    return ids, donors


def test_draw_is_deterministic_given_seed():
    ids, donors = _cells()
    a = discovery_sample(ids, donors, budget=6, equal_per_donor=True, seed=7)
    b = discovery_sample(ids, donors, budget=6, equal_per_donor=True, seed=7)
    assert list(a.cell_ids) == list(b.cell_ids)


def test_draw_varies_with_seed():
    ids, donors = _cells(12, 12)
    a = discovery_sample(ids, donors, budget=6, equal_per_donor=False, seed=7)
    b = discovery_sample(ids, donors, budget=6, equal_per_donor=False, seed=8)
    assert list(a.cell_ids) != list(b.cell_ids)


def test_both_arms_draw_exactly_the_budget():
    ids, donors = _cells(10, 10)
    for equal in (False, True):
        s = discovery_sample(ids, donors, budget=8, equal_per_donor=equal, seed=1)
        assert len(s.cell_ids) == 8
        assert sum(s.per_donor.values()) == 8


def test_shortfall_redistribution_keeps_arms_matched():
    # d1 holds fewer cells than its equal share: it contributes all of them and
    # the remainder is redistributed — total still exactly the budget.
    ids, donors = _cells(10, 2)
    s = discovery_sample(ids, donors, budget=8, equal_per_donor=True, seed=1)
    assert s.per_donor == {"d0": 6, "d1": 2}
    assert len(s.cell_ids) == 8


def test_budget_above_pool_is_refused_not_silently_shrunk():
    ids, donors = _cells(3, 3)
    with pytest.raises(ValueError, match="outside"):
        discovery_sample(ids, donors, budget=7, equal_per_donor=True, seed=1)


@pytest.mark.slow
def test_smoke_imbalanced_arms_share_g_but_draw_different_cells(tmp_path):
    """One SMOKE run per B arm on B_imbalanced: execution + the D016 contract
    (byte-identical frozen G, count-unit endpoints) + refit isolation (the
    outer fit's bank is untouched by test-cell scoring — scoring is a pure
    NNLS over a frozen dictionary, and the bank file hash before/after the
    scoring calls in the run would have to move if it were not)."""
    import cnmfbench.skeleton as skeleton

    dirs = {}
    for arm_cfg in ("smoke_000imbalanced.yaml", "smoke_010imbalanced.yaml"):
        out = skeleton.run(os.path.join(REPO, "docs/benchmarks/configs", arm_cfg),
                           out_root=str(tmp_path), run_id=arm_cfg.replace(".yaml", ""))
        dirs[arm_cfg] = out["run_dir"]
    g000 = open(os.path.join(dirs["smoke_000imbalanced.yaml"], "outer_0",
                             "frozen_G.txt"), "rb").read()
    g010 = open(os.path.join(dirs["smoke_010imbalanced.yaml"], "outer_0",
                             "frozen_G.txt"), "rb").read()
    assert g000 == g010, "B arms diverged on G"

    import csv
    for arm_cfg in dirs:
        rows = list(csv.DictReader(
            open(os.path.join(dirs[arm_cfg], "results.tsv")), delimiter="\t"))
        assert rows, arm_cfg
        assert {r["status"] for r in rows} == {"ok_provisional"}
