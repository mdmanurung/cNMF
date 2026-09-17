"""Schema conformance, controlled vocabularies, and the fence.

The TSV schemas are the interface between this programme and anyone reading its evidence
later. Nothing in the repo defined them in code before this session, so these tests are
what keeps the committed headers and the writer from drifting apart.
"""
import csv
import os

import pytest

from cnmfbench import provisional as P
from cnmfbench import records as R

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _header(name):
    with open(os.path.join(REPO, "docs/benchmarks", name), encoding="utf-8") as fh:
        return tuple(next(csv.reader(fh, delimiter="\t")))


def _ok_result(**over):
    base = dict(
        experiment_id="e1", configuration="000", arm="full_training_pool",
        dataset_id="d", independent_unit_id="donor_000", independent_unit_type="donor",
        outer_split_id="outer_0", metric="heldout_squared_prediction_error_v1",
        value="1.0", evaluation_scope="per_donor", candidate_rank=3,
        n_eligible_units=30, n_failed_units=0, status="ok_provisional",
        artifact_path="results/x",
    )
    base.update(over)
    return base


# ------------------------------------------------------------------- schema conformance


def test_results_schema_matches_the_committed_header_exactly():
    assert R.RESULTS_COLUMNS == _header("RESULTS.tsv")


def test_experiments_schema_matches_the_committed_header_exactly():
    assert R.EXPERIMENTS_COLUMNS == _header("EXPERIMENTS.tsv")


def test_exactly_the_eleven_protocol_metrics_are_allowed():
    assert len(R.METRIC_DIRECTION) == 11
    with pytest.raises(ValueError, match="not one of PROTOCOL"):
        R.result_row(**_ok_result(metric="silhouette"))


def test_direction_uses_the_section_5_1_strings():
    assert set(R.METRIC_DIRECTION.values()) == {"lower_is_better", "higher_is_better"}
    row = R.result_row(**_ok_result())
    assert row["direction"] == "lower_is_better"


def test_a_direction_contradicting_the_vocabulary_is_rejected():
    with pytest.raises(ValueError, match="contradicts"):
        R.result_row(**_ok_result(direction="higher_is_better"))


def test_selected_rank_must_be_null_on_a_fixed_rank_row():
    """§5.3. A non-null value here would be the baseline selector running while `delta`
    is null, which §2 requires to refuse."""
    assert R.result_row(**_ok_result())["selected_rank"] == ""
    with pytest.raises(ValueError, match="selected_rank must be null"):
        R.result_row(**_ok_result(selected_rank=3))


def test_none_like_strings_are_rejected_but_a_true_null_is_kept():
    """A blank means "genuinely null"; NOT_COMPUTED means "could not be produced". The
    strings that look like data but are accidents must not reach the file."""
    assert R.result_row(**_ok_result(value=None))["value"] == ""
    with pytest.raises(ValueError, match="would be written as"):
        R.result_row(**_ok_result(value="nan"))
    assert R.result_row(**_ok_result(value=R.NOT_COMPUTED))["value"] == "NOT_COMPUTED"


def test_tabs_and_newlines_are_rejected():
    with pytest.raises(ValueError, match="tab or newline"):
        R.result_row(**_ok_result(artifact_path="a\tb"))


def test_unknown_or_missing_columns_are_rejected():
    with pytest.raises(ValueError, match="unknown"):
        R.result_row(**_ok_result(extra_column="x"))
    incomplete = _ok_result()
    del incomplete["dataset_id"]
    with pytest.raises(ValueError, match="missing"):
        R.result_row(**incomplete)


def test_arm_is_not_labelled_matched_budget_by_accident():
    """The skeleton uses every training-donor cell with no budget, which is
    `upstream_full_data`'s definition applied to a training fold. Labelling it
    matched_budget would silently confound the future B comparison."""
    assert "full_training_pool" in R.ARM
    with pytest.raises(ValueError, match="arm"):
        R.result_row(**_ok_result(arm="whatever"))


def test_experiment_id_is_deterministic_and_seed_sensitive():
    args = ("000", "full_training_pool", "d", "outer_0", 3)
    a = R.make_experiment_id(*args, {"seed": 1})
    assert a == R.make_experiment_id(*args, {"seed": 1})
    assert a != R.make_experiment_id(*args, {"seed": 2})
    assert a != R.make_experiment_id("000", "full_training_pool", "d", "outer_1", 3, {"seed": 1})


def test_protocol_hash_matches_the_value_recorded_in_ablation_plan():
    import yaml

    with open(os.path.join(REPO, "docs/benchmarks/configs/ablation_plan.yaml"), encoding="utf-8") as fh:
        recorded = yaml.safe_load(fh)["protocol"]["sha256"]
    assert R.protocol_hash() == recorded


# ------------------------------------------------------------------------------ writing


def test_merge_refuses_a_duplicate_row(tmp_path):
    path = tmp_path / "RESULTS.tsv"
    R.write_rows(str(path), [], R.RESULTS_COLUMNS)
    rows = [R.result_row(**_ok_result())]
    R.merge_into_tracked(str(path), rows, R.RESULTS_COLUMNS)
    with pytest.raises(ValueError, match="already present"):
        R.merge_into_tracked(str(path), rows, R.RESULTS_COLUMNS)


def test_merge_preserves_the_header_and_appends(tmp_path):
    path = tmp_path / "RESULTS.tsv"
    R.write_rows(str(path), [], R.RESULTS_COLUMNS)
    R.merge_into_tracked(str(path), [R.result_row(**_ok_result())], R.RESULTS_COLUMNS)
    with open(path, encoding="utf-8") as fh:
        lines = list(csv.reader(fh, delimiter="\t"))
    assert tuple(lines[0]) == R.RESULTS_COLUMNS
    assert len(lines) == 2


def test_merge_rejects_a_mismatched_header(tmp_path):
    path = tmp_path / "bad.tsv"
    path.write_text("a\tb\n", encoding="utf-8")
    with pytest.raises(ValueError, match="header"):
        R.merge_into_tracked(str(path), [], R.RESULTS_COLUMNS)


# ------------------------------------------------- the committed evidence is consistent


def _tracked(name):
    with open(os.path.join(REPO, "docs/benchmarks", name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_results_and_experiments_agree_on_cost():
    """The defect this guards against shipped once: RESULTS timed only the marginal
    consensus+scoring while EXPERIMENTS added an amortised share of the shared fit, so the
    two files disagreed by ~2.2x for the same experiment_id and the column a comparison
    reads made factorization free. Both are now rendered from one object; this keeps them
    that way."""
    results = {(r["experiment_id"], r["metric"]): r["value"] for r in _tracked("RESULTS.tsv")}
    experiments = _tracked("EXPERIMENTS.tsv")
    if not experiments:
        pytest.skip("no rows written yet")
    for e in experiments:
        for metric, column in (("wall_seconds_v1", "wall_seconds"),
                               ("cpu_seconds_v1", "cpu_seconds"),
                               ("peak_memory_mb_v1", "peak_memory_mb")):
            assert results[(e["experiment_id"], metric)] == e[column], (
                f"{e['experiment_id']}: {metric} != {column}"
            )


def test_shared_fit_cost_is_attributed_exactly_once():
    """One prepare/factorize/combine per fold serves every candidate rank, so its cost
    belongs to no single rank. It gets its own row with candidate_rank empty; per-rank
    rows carry marginal cost only. Summing the fold's rows therefore gives the true total
    with no double counting."""
    experiments = _tracked("EXPERIMENTS.tsv")
    if not experiments:
        pytest.skip("no rows written yet")
    # Group by the whole fold identity, not by `outer_split_id` alone. Every run names its
    # folds `outer_0`, `outer_1`, ..., so once the tracked file holds more than one run the
    # bare split id collides across them and this test reads two runs' fit rows as two fit
    # rows for one fold. `dataset_id` carries scenario, tier and replicate; with the
    # configuration bits and the split id it identifies the fold uniquely.
    by_fold = {}
    for e in experiments:
        key = (e["dataset_id"], e["outer_split_id"], e["arm"],
               e["feature_A"], e["feature_B"], e["feature_C"])
        by_fold.setdefault(key, []).append(e)
    for fold, rows in by_fold.items():
        fit = [r for r in rows if r["candidate_rank"] == ""]
        per_rank = [r for r in rows if r["candidate_rank"] != ""]
        assert len(fit) == 1, f"{fold}: expected exactly one fit-scope row, got {len(fit)}"
        assert per_rank, f"{fold}: no per-rank rows"
        # The shared fit dominates; a per-rank row carrying it too would show up here.
        assert float(fit[0]["wall_seconds"]) > max(float(r["wall_seconds"]) for r in per_rank)


def test_every_written_row_is_provisional_and_cannot_promote():
    """While the fence stands, every row must say so and must sit at a tier that cannot
    promote a feature. The two must not drift apart."""
    rows = _tracked("RESULTS.tsv")
    if not rows:
        pytest.skip("no rows written yet")
    assert not P.registry_is_empty()
    assert {r["status"] for r in rows} == {"ok_provisional"}
    assert {e["evidence_tier"] for e in _tracked("EXPERIMENTS.tsv")} <= {"SMOKE", "DEVELOPMENT"}
    assert all(e["prototype"] == "true" for e in _tracked("EXPERIMENTS.tsv"))


# -------------------------------------------------------------------------- the fence


def test_registry_and_decorators_agree_in_both_directions():
    """A registry entry without a decorator un-fences a component silently; a decorator
    without an entry cannot be read by the gate. Both must fail loudly."""
    import importlib
    import pkgutil

    import cnmfbench

    decorated = set()
    for mod in pkgutil.iter_modules(cnmfbench.__path__):
        m = importlib.import_module(f"cnmfbench.{mod.name}")
        for obj in vars(m).values():
            cid = getattr(obj, "__cnmfbench_provisional__", None)
            if cid:
                decorated.add(cid)
    assert decorated == set(P.PROVISIONAL)


def test_the_gate_is_blocked_while_components_are_provisional():
    assert not P.registry_is_empty()


def test_every_provisional_component_names_a_real_ledger_task():
    for c in P.PROVISIONAL.values():
        assert c.owner_task.startswith("P0-")
        assert c.reason and c.hardening_requires


def test_calling_a_provisional_component_records_it():
    from cnmfbench.splits import gene_panel

    P.reset_touched()
    assert P.touched() == ()
    gene_panel([f"g{i}" for i in range(10)], 0.5, 1)
    assert "splits.gene_panel" in P.touched()


def test_cited_rows_check_is_scoped_not_a_whole_file_scan():
    """Provisional rows stay in RESULTS.tsv forever and correctly. A whole-file scan
    would block the gate permanently no matter how much hardening happened."""
    rows = [{"experiment_id": "old", "status": "ok_provisional"},
            {"experiment_id": "new", "status": "ok"}]
    assert P.cited_rows_are_not_provisional(rows, ["new"])
    assert not P.cited_rows_are_not_provisional(rows, ["old"])


def test_the_throwaway_reference_is_not_imported_by_the_real_path():
    """D006's named hazard: `diagnostics._score_split` must be read as reference and not
    become the implementation. It is also cited P0-03 evidence, so it must not change."""
    import pathlib

    for path in pathlib.Path(REPO, "cnmfbench").glob("*.py"):
        if path.name == "diagnostics.py":
            continue
        text = path.read_text(encoding="utf-8")
        assert "_score_split" not in text, f"{path.name} references the throwaway scorer"
        assert "_equal_donor_mean_sse" not in text, f"{path.name} references the throwaway aggregator"


# ------------------------------------------------------------------- the pooling guard


def test_pooling_across_folds_is_refused():
    """Measured at SMOKE: Jaccard(G_0, G_1) = 0.639, so the folds are not on a common
    axis and averaging them describes no measurement. The schema cannot express that;
    preprocessing_hash can, and this is what uses it."""
    from cnmfbench.analysis import PoolingError, assert_poolable, pooling_groups

    rows, experiments = _tracked("RESULTS.tsv"), _tracked("EXPERIMENTS.tsv")
    if not rows:
        pytest.skip("no rows written yet")
    groups = pooling_groups(rows, experiments)
    assert len(groups) > 1, "expected per-fold preprocessing_hash values to differ"
    with pytest.raises(PoolingError, match="common axis"):
        assert_poolable(rows, experiments)
    # Within one group it must succeed — the guard must not block valid aggregation.
    assert assert_poolable(next(iter(groups.values())), experiments)


def test_pooling_guard_refuses_rows_with_no_provenance():
    from cnmfbench.analysis import PoolingError, assert_poolable

    with pytest.raises(PoolingError, match="absent from EXPERIMENTS"):
        assert_poolable([{"experiment_id": "ghost"}], [])
