"""P1-02 feature A: admission, budget guards, selection rules, row identity.

Acceptance: selection tests; no outer-data access; unchanged candidate fits.
"""
import os

import pytest
import yaml

from cnmfbench import skeleton
from cnmfbench.contract import ContractViolation
from cnmfbench.records import make_experiment_id
from cnmfbench.selector import select_rank_predictive

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load(name):
    with open(os.path.join(REPO, "docs/benchmarks/configs", name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _ablation():
    with open(os.path.join(REPO, "docs/benchmarks/configs/ablation_plan.yaml"),
              encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_read_delta_matches_the_frozen_v1_1_value():
    assert skeleton.read_delta() == 0.04812


def test_predictive_selector_takes_the_minimum():
    k, boundary = select_rank_predictive({2: 1.5, 3: 1.2, 4: 1.8})
    assert (k, boundary) == (3, False)


def test_predictive_selector_breaks_exact_ties_toward_smaller_k():
    k, _ = select_rank_predictive({2: 1.0, 3: 1.0, 4: 2.0})
    assert k == 2


def test_predictive_selector_flags_grid_endpoints_but_never_expands():
    k, boundary = select_rank_predictive({2: 1.0, 3: 2.0, 4: 3.0})
    assert (k, boundary) == (2, True)


def test_predictive_selector_refuses_an_empty_grid():
    with pytest.raises(ContractViolation, match="no inner-validation scores"):
        select_rank_predictive({})


def test_a_on_config_is_admitted_now_delta_is_set():
    cfg = _load("smoke_100ab48.yaml")
    skeleton.check_preconditions(cfg, _ablation())  # must not raise


def test_a_on_with_outer_only_budget_is_refused_closed_form():
    cfg = _load("smoke_100ab48.yaml")
    cfg["discovery"]["cell_budget"] = 72  # fits the outer pool (120), not an inner pool (60)
    with pytest.raises(ContractViolation, match="inner-training pool"):
        skeleton.check_preconditions(cfg, _ablation())


def test_inner_budget_scales_over_cells_not_donors():
    assert skeleton._inner_budget(48, 60, 120) == 24
    assert skeleton._inner_budget(960, 1200, 2400) == 480
    with pytest.raises(ContractViolation, match="leaves nothing"):
        skeleton._inner_budget(1, 1, 10000)


def test_selected_rank_row_gets_a_distinct_id_but_fixed_ids_do_not_move():
    seeds = {"seed": 1701, "panel_seed": 20260917}
    fixed = make_experiment_id("100", "matched_budget", "d", "outer_0", 3, seeds,
                               variant="ab48")
    selected = make_experiment_id("100", "matched_budget", "d", "outer_0", 3, seeds,
                                  variant="ab48", selected_rank=3)
    assert fixed != selected
    # Pinned: the fixed-rank id is bit-identical to the pre-P1-02 scheme, which
    # knew no selected_rank parameter. If this literal changes, an identifier
    # that existing tracked rows depend on has moved.
    # (Re-pinned at v1.2/D045: PROTOCOL_VERSION 1.0.1→1.2 enters the payload, so
    # all v1.2-era ids live in a new identity domain BY DESIGN; v1.0.1/1.1 ids in
    # tracked TSVs are unaffected because no existing row is regenerated.)
    assert fixed == "100-matched_budget-d-ab48-outer_0-k3-13bf0015f745"
    assert selected == "100-matched_budget-d-ab48-sel3-outer_0-k3-f9ac8b459175"


@pytest.mark.slow
def test_a_on_leaves_candidate_fits_unchanged(tmp_path):
    """P1-02's core invariant: A changes which rank is read off, never how a fit
    is computed. Fixed-rank rows from the A-ON run must equal the A-OFF run's at
    the same budget, seed, panel and folds — compared on content (ids differ by
    configuration prefix by design)."""
    import csv

    # Cost rows are excluded by design: the A-ON fit-scope row carries the inner
    # fits' cost (D024's argument), so it must differ. What must not differ is
    # every evaluation value at every rank.
    COST = {"wall_seconds_v1", "cpu_seconds_v1", "peak_memory_mb_v1",
            "failed_fits_v1"}

    def fixed_content(run_dir):
        rows = list(csv.DictReader(open(os.path.join(run_dir, "results.tsv")),
                                   delimiter="\t"))
        out = []
        for r in rows:
            if r["selected_rank"] not in ("", None):
                continue
            if r["metric"] in COST or r["candidate_rank"] in ("", None):
                continue
            # Experiment-scope ids embed the configuration prefix (100 vs 000)
            # by design; donor ids are shared and stay in the key.
            unit = r["independent_unit_id"] if r["independent_unit_type"] == "donor" else ""
            out.append((r["metric"], r["candidate_rank"], unit,
                        r["evaluation_scope"], r["value"]))
        return sorted(out)

    on = skeleton.run(os.path.join(REPO, "docs/benchmarks/configs/smoke_100ab48.yaml"),
                      out_root=str(tmp_path), run_id="a_on")["run_dir"]
    off = skeleton.run(os.path.join(REPO, "docs/benchmarks/configs/smoke_000ab48.yaml"),
                       out_root=str(tmp_path), run_id="a_off")["run_dir"]
    assert fixed_content(on) == fixed_content(off)


@pytest.mark.slow
def test_smoke_a_on_run_selects_and_pairs(tmp_path):
    """End-to-end A-ON at SMOKE: inner selection runs, both selectors emit
    selected-rank rows reusing the fixed-rank fits, and no outer-test donor
    reaches an inner fit."""
    import anndata as ad

    out = skeleton.run(os.path.join(REPO, "docs/benchmarks/configs/smoke_100ab48.yaml"),
                       out_root=str(tmp_path), run_id="a_smoke")
    run_dir = out["run_dir"]
    import csv
    rows = list(csv.DictReader(open(os.path.join(run_dir, "results.tsv")),
                               delimiter="\t"))
    sel = [r for r in rows if r["selected_rank"] not in ("", None)]
    assert sel, "no selected-rank rows emitted"
    assert all(r["selected_rank"] == r["candidate_rank"] for r in sel)
    cfgs = {(r["configuration"], r["selected_rank"]) for r in sel}
    a_side = {c for c in cfgs if c[0] == "100"}
    base_side = {c for c in cfgs if c[0] == "000"}
    assert a_side and base_side, f"both selectors must emit: {sorted(cfgs)}"
    assert all(int(k) in (2, 3, 4) for _, k in cfgs)
    # No outer-data access: no inner fit input may hold an outer-test donor.
    # Outer test donors are recomputed from the deterministic splitter, not read
    # from the run (which would trust the thing being tested).
    from cnmfbench.splits import outer_donor_folds

    ds_donors = list(ad.read_h5ad(
        os.path.join(run_dir, "dataset", "counts.h5ad")).obs["donor_id"])
    test_by_fold = {f.outer_split_id: set(f.test_donors)
                    for f in outer_donor_folds(ds_donors, 2, 1701)}
    checked = 0
    for outer_id in ("outer_0", "outer_1"):
        inner_dir = os.path.join(run_dir, outer_id, "inner")
        assert os.path.isdir(inner_dir), f"A-ON ran no inner fold in {outer_id}"
        for f in os.listdir(inner_dir):
            if f.endswith("_counts.h5ad"):
                obs = ad.read_h5ad(os.path.join(inner_dir, f)).obs
                assert not (set(obs["donor_id"]) & test_by_fold[outer_id]), f
                checked += 1
    assert checked >= 4, "expected ≥4 inner input files (pool + sample per inner fold)"
